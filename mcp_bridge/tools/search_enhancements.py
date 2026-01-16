import sys
import logging
import asyncio
from mcp_bridge.tools.semantic_search import semantic_search, get_store, EmbeddingProvider

logger = logging.getLogger(__name__)

def _check_index_exists(store) -> bool:
    """Check if index exists (duplicated from semantic_search.py helper)"""
    try:
        stats = store.get_stats()
        return stats.get("chunks_indexed", 0) > 0
    except Exception:
        return False

async def multi_query_search(
    query: str,
    project_path: str = ".",
    n_results: int = 10,
    num_expansions: int = 3,
    language: str | None = None,
    node_type: str | None = None,
    provider: EmbeddingProvider = "ollama",
) -> str:
    """
    Search with LLM-expanded query variations for better recall.
    """
    try:
        from mcp_bridge.auth.token_store import TokenStore
        from mcp_bridge.tools.model_invoke import invoke_gemini
    except ImportError:
        return "Error: Dependencies for query expansion not available."

    print(f"🔄 Expanding query: '{query}'...", file=sys.stderr)

    # 1. Generate variations
    token_store = TokenStore()
    prompt = f"""You are a query expansion specialist.
Generate {num_expansions} different semantic variations of this search query:
"{query}"

Focus on synonyms, related concepts, and technical terminology.
Return ONLY the variations, one per line. No numbering, no preamble."""

    try:
        variations_text = await invoke_gemini(
            token_store=token_store,
            prompt=prompt,
            model="gemini-3-flash",
            temperature=0.7,
            agent_context={"agent_type": "explore", "description": "Expanding search query"}
        )
        variations = [v.strip() for v in variations_text.split("\n") if v.strip()]
        # Remove any "Here are..." prefixes if model ignores instructions
        variations = [v for v in variations if not v.lower().startswith("here")]
        # Limit to num_expansions
        variations = variations[:num_expansions]
        print(f"✅ Generated {len(variations)} variations", file=sys.stderr)
    except Exception as e:
        logger.warning(f"Query expansion failed: {e}")
        variations = []

    queries = [query] + variations
    
    # 2. Run searches in parallel
    store = get_store(project_path, provider)
    
    if not _check_index_exists(store):
        return "Index required. Run semantic_search first to trigger creation."

    # Use store.search directly to get raw results
    tasks = [
        store.search(
            q, n_results, language, node_type, is_async=None, decorator=None, base_class=None
        ) for q in queries
    ]
    
    results_lists = await asyncio.gather(*tasks)
    
    # 3. Reciprocal Rank Fusion (RRF)
    # RRF score = 1 / (k + rank)
    k = 60
    rrf_scores = {}
    
    for results in results_lists:
        if not results or isinstance(results, dict) and "error" in results: 
             # store.search might return dict with error or list of dicts
             if isinstance(results, list) and len(results) > 0 and "error" in results[0]:
                 continue
             if isinstance(results, dict) and "error" in results:
                 continue
        
        if not isinstance(results, list):
            continue
            
        for rank, item in enumerate(results):
            # Create a unique key for the code chunk
            key = f"{item['file']}:{item['lines']}"
            
            if key not in rrf_scores:
                rrf_scores[key] = {
                    "item": item,
                    "score": 0.0,
                    "matched_queries": set()
                }
            
            rrf_scores[key]["score"] += 1.0 / (k + rank + 1)
    
    # Sort by score
    sorted_items = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)
    top_results = sorted_items[:n_results]
    
    if not top_results:
        return "No results found"

    lines = [f"Found {len(top_results)} results for '{query}' (expanded to {len(queries)} queries)\n"]
    for i, entry in enumerate(top_results, 1):
        r = entry["item"]
        lines.append(f"{i}. {r['file']}:{r['lines']} (score: {entry['score']:.4f})")
        lines.append(f"```{r['language']}")
        lines.append(r["code_preview"])
        lines.append("```\n")

    return "\n".join(lines)


async def decomposed_search(
    query: str,
    project_path: str = ".",
    n_results: int = 10,
    language: str | None = None,
    node_type: str | None = None,
    provider: EmbeddingProvider = "ollama",
) -> str:
    """
    Search by decomposing complex queries into focused sub-questions.
    """
    try:
        from mcp_bridge.auth.token_store import TokenStore
        from mcp_bridge.tools.model_invoke import invoke_gemini
    except ImportError:
        return "Error: Dependencies for query decomposition not available."

    print(f"🔄 Decomposing query: '{query}'...", file=sys.stderr)

    token_store = TokenStore()
    prompt = f"""You are a query decomposition specialist.
Break this complex code search query into 2-4 focused, atomic sub-queries:
"{query}"

Each sub-query should look for a specific part of the system or concept.
Return ONLY the sub-queries, one per line. No numbering."""

    try:
        subqueries_text = await invoke_gemini(
            token_store=token_store,
            prompt=prompt,
            model="gemini-3-flash",
            temperature=0.7,
            agent_context={"agent_type": "explore", "description": "Decomposing search query"}
        )
        subqueries = [q.strip() for q in subqueries_text.split("\n") if q.strip()]
        subqueries = [q for q in subqueries if not q.lower().startswith("here")]
        print(f"✅ Decomposed into {len(subqueries)} sub-queries", file=sys.stderr)
    except Exception as e:
        logger.warning(f"Decomposition failed: {e}")
        return await semantic_search(query, project_path, n_results, language, node_type, provider=provider)

    if not subqueries:
        return await semantic_search(query, project_path, n_results, language, node_type, provider=provider)

    store = get_store(project_path, provider)
    if not _check_index_exists(store):
        return "Index required. Run semantic_search first to trigger creation."

    tasks = [
        store.search(
            q, n_results, language, node_type, is_async=None, decorator=None, base_class=None
        ) for q in subqueries
    ]
    
    results_lists = await asyncio.gather(*tasks)
    
    lines = [f"Decomposed '{query}' into {len(subqueries)} parts:\n"]
    
    for q, results in zip(subqueries, results_lists):
        lines.append(f"### Sub-query: {q}")
        if not results:
             lines.append("No results found.\n")
             continue
             
        if isinstance(results, dict) and "error" in results:
             lines.append(f"Error: {results['error']}\n")
             continue
             
        if isinstance(results, list) and len(results) > 0 and "error" in results[0]:
             lines.append(f"Error: {results[0]['error']}\n")
             continue
            
        # Just show top 3-5 per subquery to save tokens
        for i, r in enumerate(results[:5], 1):
            lines.append(f"{i}. {r['file']}:{r['lines']} (relevance: {r['relevance']})")
            lines.append(f"```{r['language']}")
            lines.append(r["code_preview"])
            lines.append("```\n")
            
    return "\n".join(lines)


async def enhanced_search(
    query: str,
    project_path: str = ".",
    n_results: int = 10,
    mode: str = "auto",
    language: str | None = None,
    node_type: str | None = None,
    provider: EmbeddingProvider = "ollama",
) -> str:
    """
    Unified enhanced search.
    mode: 'auto', 'expand', 'decompose', 'both'
    """
    
    if mode == "expand":
        return await multi_query_search(query, project_path, n_results, 3, language, node_type, provider)
    elif mode == "decompose":
        return await decomposed_search(query, project_path, n_results, language, node_type, provider)
    elif mode == "auto":
        # Simple heuristic: if query has "and" or is long (> 10 words), decompose. Else expand.
        if " and " in query.lower() or len(query.split()) > 10:
            return await decomposed_search(query, project_path, n_results, language, node_type, provider)
        else:
            return await multi_query_search(query, project_path, n_results, 3, language, node_type, provider)
    elif mode == "both":
        return await multi_query_search(query, project_path, n_results, 3, language, node_type, provider)
        
    return await semantic_search(query, project_path, n_results, language, node_type, provider=provider)
