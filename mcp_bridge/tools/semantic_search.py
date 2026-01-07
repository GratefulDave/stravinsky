"""
Semantic Code Search - Vector-based code understanding

Uses ChromaDB for persistent vector storage with multiple embedding providers:
- Ollama (local, free) - nomic-embed-text (768 dims)
- Mxbai (local, free) - mxbai-embed-large (1024 dims, better for code)
- Gemini (cloud, OAuth) - gemini-embedding-001 (768-3072 dims)
- OpenAI (cloud, OAuth) - text-embedding-3-small (1536 dims)
- HuggingFace (cloud, token) - sentence-transformers/all-mpnet-base-v2 (768 dims)

Enables natural language queries like "find authentication logic" without
requiring exact pattern matching.

Architecture:
- Per-project ChromaDB storage at ~/.stravinsky/vectordb/<project_hash>/
- Lazy initialization on first query
- Provider abstraction for embedding generation
- Chunking strategy: function/class level with context
"""

import hashlib
import logging
import sys
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from mcp_bridge.auth.token_store import TokenStore

logger = logging.getLogger(__name__)


# Lazy imports for watchdog (avoid startup cost)
_watchdog = None
_watchdog_import_lock = threading.Lock()


def get_watchdog():
    """Lazy import of watchdog components for file watching."""
    global _watchdog
    if _watchdog is None:
        with _watchdog_import_lock:
            if _watchdog is None:
                from watchdog.observers import Observer
                from watchdog.events import FileSystemEventHandler

                _watchdog = {"Observer": Observer, "FileSystemEventHandler": FileSystemEventHandler}
    return _watchdog

# Embedding provider type
EmbeddingProvider = Literal["ollama", "mxbai", "gemini", "openai", "huggingface"]

# Lazy imports to avoid startup cost
_chromadb = None
_ollama = None
_httpx = None
_filelock = None
_import_lock = threading.Lock()


def get_filelock():
    global _filelock
    if _filelock is None:
        with _import_lock:
            if _filelock is None:
                import filelock

                _filelock = filelock
    return _filelock


def get_chromadb():
    global _chromadb
    if _chromadb is None:
        with _import_lock:
            if _chromadb is None:
                import chromadb

                _chromadb = chromadb
    return _chromadb


def get_ollama():
    global _ollama
    if _ollama is None:
        with _import_lock:
            if _ollama is None:
                import ollama

                _ollama = ollama
    return _ollama


def get_httpx():
    global _httpx
    if _httpx is None:
        with _import_lock:
            if _httpx is None:
                import httpx

                _httpx = httpx
    return _httpx


# ========================
# EMBEDDING PROVIDERS
# ========================


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding vector for text."""
        pass

    @abstractmethod
    async def check_available(self) -> bool:
        """Check if the provider is available and ready."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension for this provider."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name."""
        pass


class OllamaProvider(BaseEmbeddingProvider):
    """Ollama local embedding provider using nomic-embed-text."""

    MODEL = "nomic-embed-text"
    DIMENSION = 768

    def __init__(self):
        self._available: bool | None = None

    @property
    def dimension(self) -> int:
        return self.DIMENSION

    @property
    def name(self) -> str:
        return "ollama"

    async def check_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            ollama = get_ollama()
            models = ollama.list()
            model_names = [m.model for m in models.models] if hasattr(models, "models") else []

            if not any(name and self.MODEL in name for name in model_names):
                print(
                    f"⚠️  Embedding model '{self.MODEL}' not found. Run: ollama pull {self.MODEL}",
                    file=sys.stderr,
                )
                self._available = False
                return False

            self._available = True
            return True
        except Exception as e:
            print(f"⚠️  Ollama not available: {e}. Start with: ollama serve", file=sys.stderr)
            self._available = False
            return False

    async def get_embedding(self, text: str) -> list[float]:
        ollama = get_ollama()
        # nomic-embed-text has 8192 token context. Code can be 1-2 chars/token.
        # Truncate to 2000 chars (~1000-2000 tokens) for larger safety margin
        truncated = text[:2000] if len(text) > 2000 else text
        response = ollama.embeddings(model=self.MODEL, prompt=truncated)
        return response["embedding"]


class GeminiProvider(BaseEmbeddingProvider):
    """Gemini embedding provider using OAuth authentication."""

    MODEL = "gemini-embedding-001"
    DIMENSION = 768  # Using 768 for efficiency, can be up to 3072

    def __init__(self):
        self._available: bool | None = None
        self._token_store = None

    def _get_token_store(self):
        if self._token_store is None:
            from ..auth.token_store import TokenStore

            self._token_store = TokenStore()
        return self._token_store

    @property
    def dimension(self) -> int:
        return self.DIMENSION

    @property
    def name(self) -> str:
        return "gemini"

    async def check_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            token_store = self._get_token_store()
            access_token = token_store.get_access_token("gemini")

            if not access_token:
                print(
                    "⚠️  Gemini not authenticated. Run: stravinsky-auth login gemini",
                    file=sys.stderr,
                )
                self._available = False
                return False

            self._available = True
            return True
        except Exception as e:
            print(f"⚠️  Gemini not available: {e}", file=sys.stderr)
            self._available = False
            return False

    async def get_embedding(self, text: str) -> list[float]:
        import os

        from ..auth.oauth import (
            ANTIGRAVITY_DEFAULT_PROJECT_ID,
            ANTIGRAVITY_ENDPOINTS,
            ANTIGRAVITY_HEADERS,
        )

        token_store = self._get_token_store()
        access_token = token_store.get_access_token("gemini")

        if not access_token:
            raise ValueError("Not authenticated with Gemini. Run: stravinsky-auth login gemini")

        httpx = get_httpx()

        # Use Antigravity endpoint for embeddings (same auth as invoke_gemini)
        project_id = os.getenv("STRAVINSKY_ANTIGRAVITY_PROJECT_ID", ANTIGRAVITY_DEFAULT_PROJECT_ID)

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            **ANTIGRAVITY_HEADERS,
        }

        # Wrap request for Antigravity API
        import uuid

        inner_payload = {
            "model": f"models/{self.MODEL}",
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": self.DIMENSION,
        }

        wrapped_payload = {
            "project": project_id,
            "model": self.MODEL,
            "userAgent": "antigravity",
            "requestId": f"embed-{uuid.uuid4()}",
            "request": inner_payload,
        }

        # Try endpoints in order
        last_error = None
        async with httpx.AsyncClient(timeout=60.0) as client:
            for endpoint in ANTIGRAVITY_ENDPOINTS:
                api_url = f"{endpoint}/v1internal:embedContent"

                try:
                    response = await client.post(
                        api_url,
                        headers=headers,
                        json=wrapped_payload,
                    )

                    if response.status_code in (401, 403):
                        last_error = Exception(f"{response.status_code} from {endpoint}")
                        continue

                    response.raise_for_status()
                    data = response.json()

                    # Extract embedding from response
                    inner_response = data.get("response", data)
                    embedding = inner_response.get("embedding", {})
                    values = embedding.get("values", [])

                    if values:
                        return values

                    raise ValueError(f"No embedding values in response: {data}")

                except Exception as e:
                    last_error = e
                    continue

        raise ValueError(f"All Antigravity endpoints failed for embeddings: {last_error}")


class OpenAIProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider using OAuth authentication."""

    MODEL = "text-embedding-3-small"
    DIMENSION = 1536

    def __init__(self):
        self._available: bool | None = None
        self._token_store = None

    def _get_token_store(self):
        if self._token_store is None:
            from ..auth.token_store import TokenStore

            self._token_store = TokenStore()
        return self._token_store

    @property
    def dimension(self) -> int:
        return self.DIMENSION

    @property
    def name(self) -> str:
        return "openai"

    async def check_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            token_store = self._get_token_store()
            access_token = token_store.get_access_token("openai")

            if not access_token:
                print(
                    "⚠️  OpenAI not authenticated. Run: stravinsky-auth login openai",
                    file=sys.stderr,
                )
                self._available = False
                return False

            self._available = True
            return True
        except Exception as e:
            print(f"⚠️  OpenAI not available: {e}", file=sys.stderr)
            self._available = False
            return False

    async def get_embedding(self, text: str) -> list[float]:
        token_store = self._get_token_store()
        access_token = token_store.get_access_token("openai")

        if not access_token:
            raise ValueError("Not authenticated with OpenAI. Run: stravinsky-auth login openai")

        httpx = get_httpx()

        # Use standard OpenAI API for embeddings
        api_url = "https://api.openai.com/v1/embeddings"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.MODEL,
            "input": text,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)

            if response.status_code == 401:
                raise ValueError("OpenAI authentication failed. Run: stravinsky-auth login openai")

            response.raise_for_status()
            data = response.json()

            # Extract embedding from response
            embeddings = data.get("data", [])
            if embeddings and "embedding" in embeddings[0]:
                return embeddings[0]["embedding"]

            raise ValueError(f"No embedding in response: {data}")


class MxbaiProvider(BaseEmbeddingProvider):
    """Ollama local embedding provider using mxbai-embed-large (better for code).

    mxbai-embed-large is a 1024-dimensional model optimized for code understanding.
    It generally outperforms nomic-embed-text on code-related retrieval tasks.
    """

    MODEL = "mxbai-embed-large"
    DIMENSION = 1024

    def __init__(self):
        self._available: bool | None = None

    @property
    def dimension(self) -> int:
        return self.DIMENSION

    @property
    def name(self) -> str:
        return "mxbai"

    async def check_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            ollama = get_ollama()
            models = ollama.list()
            model_names = [m.model for m in models.models] if hasattr(models, "models") else []

            if not any(name and self.MODEL in name for name in model_names):
                print(
                    f"⚠️  Embedding model '{self.MODEL}' not found. Run: ollama pull {self.MODEL}",
                    file=sys.stderr,
                )
                self._available = False
                return False

            self._available = True
            return True
        except Exception as e:
            print(f"⚠️  Ollama not available: {e}. Start with: ollama serve", file=sys.stderr)
            self._available = False
            return False

    async def get_embedding(self, text: str) -> list[float]:
        ollama = get_ollama()
        # mxbai-embed-large has 512 token context. Code can be 1-2 chars/token.
        # Truncate to 2000 chars (~1000-2000 tokens) for safety margin
        truncated = text[:2000] if len(text) > 2000 else text
        response = ollama.embeddings(model=self.MODEL, prompt=truncated)
        return response["embedding"]


class HuggingFaceProvider(BaseEmbeddingProvider):
    """Hugging Face Inference API embedding provider.

    Uses the Hugging Face Inference API for embeddings. Requires HF_TOKEN from:
    1. Environment variable: HF_TOKEN or HUGGING_FACE_HUB_TOKEN
    2. HF CLI config: ~/.cache/huggingface/token or ~/.huggingface/token

    Default model: sentence-transformers/all-mpnet-base-v2 (768 dims, high quality)
    """

    DEFAULT_MODEL = "sentence-transformers/all-mpnet-base-v2"
    DEFAULT_DIMENSION = 768

    def __init__(self, model: str | None = None):
        self._available: bool | None = None
        self._model = model or self.DEFAULT_MODEL
        # Dimension varies by model, but we'll use default for common models
        self._dimension = self.DEFAULT_DIMENSION
        self._token: str | None = None

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def name(self) -> str:
        return "huggingface"

    def _get_hf_token(self) -> str | None:
        """Discover HF token from environment or CLI config."""
        import os

        # Check environment variables first
        token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
        if token:
            return token

        # Check HF CLI config locations
        hf_token_paths = [
            Path.home() / ".cache" / "huggingface" / "token",
            Path.home() / ".huggingface" / "token",
        ]

        for token_path in hf_token_paths:
            if token_path.exists():
                try:
                    return token_path.read_text().strip()
                except Exception:
                    continue

        return None

    async def check_available(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            self._token = self._get_hf_token()
            if not self._token:
                print(
                    "⚠️  Hugging Face token not found. Run: huggingface-cli login or set HF_TOKEN env var",
                    file=sys.stderr,
                )
                self._available = False
                return False

            self._available = True
            return True
        except Exception as e:
            print(f"⚠️  Hugging Face not available: {e}", file=sys.stderr)
            self._available = False
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
    )
    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding from HF Inference API with retry logic."""
        if not self._token:
            self._token = self._get_hf_token()
            if not self._token:
                raise ValueError(
                    "Hugging Face token not found. Run: huggingface-cli login or set HF_TOKEN"
                )

        httpx_client = get_httpx()

        # HF Serverless Inference API endpoint
        # Note: Free tier may have limited availability for some models
        api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self._model}"

        headers = {
            "Authorization": f"Bearer {self._token}",
        }

        # Truncate text to reasonable length (most models have 512 token limit)
        # ~2000 chars ≈ 500 tokens for safety
        truncated = text[:2000] if len(text) > 2000 else text

        # HF Inference API accepts raw JSON with inputs field
        payload = {"inputs": [truncated], "options": {"wait_for_model": True}}

        async with httpx_client.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)

            # Handle specific error codes
            if response.status_code == 401:
                raise ValueError(
                    "Hugging Face authentication failed. Run: huggingface-cli login or set HF_TOKEN"
                )
            elif response.status_code == 410:
                # Model removed from free tier
                raise ValueError(
                    f"Model {self._model} is no longer available on HF free Inference API (410 Gone). "
                    "Try a different model or use Ollama for local embeddings instead."
                )
            elif response.status_code == 503:
                # Model loading - retry will handle this
                logger.info(f"Model {self._model} is loading, retrying...")
                response.raise_for_status()
            elif response.status_code == 429:
                # Rate limit - retry will handle with exponential backoff
                logger.warning("HF API rate limit hit, retrying with backoff...")
                response.raise_for_status()

            response.raise_for_status()

            # Response is a single embedding vector (list of floats)
            embedding = response.json()

            # Handle different response formats
            if isinstance(embedding, list):
                # Direct embedding or batch with single item
                if isinstance(embedding[0], (int, float)):
                    return embedding
                elif isinstance(embedding[0], list):
                    # Batch response with single embedding
                    return embedding[0]

            raise ValueError(f"Unexpected response format from HF API: {type(embedding)}")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding support for HF API.

        HF API supports batch requests, so we can send multiple texts at once.
        """
        if not texts:
            return []

        if not self._token:
            self._token = self._get_hf_token()
            if not self._token:
                raise ValueError(
                    "Hugging Face token not found. Run: huggingface-cli login or set HF_TOKEN"
                )

        httpx_client = get_httpx()

        # HF Serverless Inference API endpoint
        api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self._model}"

        headers = {
            "Authorization": f"Bearer {self._token}",
        }

        # Truncate all texts
        truncated_texts = [text[:2000] if len(text) > 2000 else text for text in texts]

        payload = {"inputs": truncated_texts, "options": {"wait_for_model": True}}

        async with httpx_client.AsyncClient(timeout=120.0) as client:
            response = await client.post(api_url, headers=headers, json=payload)

            if response.status_code == 401:
                raise ValueError(
                    "Hugging Face authentication failed. Run: huggingface-cli login or set HF_TOKEN"
                )

            response.raise_for_status()

            embeddings = response.json()

            # Response should be a list of embeddings
            if isinstance(embeddings, list) and all(isinstance(e, list) for e in embeddings):
                return embeddings

            raise ValueError(f"Unexpected batch response format from HF API: {type(embeddings)}")


# Embedding provider instance cache
_embedding_provider_cache: dict[str, BaseEmbeddingProvider] = {}
_embedding_provider_lock = threading.Lock()


def get_embedding_provider(provider: EmbeddingProvider) -> BaseEmbeddingProvider:
    """Factory function to get an embedding provider instance with caching."""
    if provider not in _embedding_provider_cache:
        with _embedding_provider_lock:
            # Double-check pattern to avoid race condition
            if provider not in _embedding_provider_cache:
                providers = {
                    "ollama": OllamaProvider,
                    "mxbai": MxbaiProvider,
                    "gemini": GeminiProvider,
                    "openai": OpenAIProvider,
                    "huggingface": HuggingFaceProvider,
                }

                if provider not in providers:
                    raise ValueError(f"Unknown provider: {provider}. Available: {list(providers.keys())}")

                _embedding_provider_cache[provider] = providers[provider]()

    return _embedding_provider_cache[provider]


class CodebaseVectorStore:
    """
    Persistent vector store for a single codebase.

    Storage: ~/.stravinsky/vectordb/<project_hash>_<provider>/
    Embedding: Configurable via provider (ollama, gemini, openai)
    """

    CHUNK_SIZE = 50  # lines per chunk
    CHUNK_OVERLAP = 10  # lines of overlap between chunks

    # File patterns to index
    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".go",
        ".rs",
        ".rb",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".swift",
        ".kt",
        ".scala",
        ".vue",
        ".svelte",
        ".md",
        ".txt",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
    }

    # Directories to skip
    SKIP_DIRS = {
        "node_modules",
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "target",
        ".tox",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "coverage",
        ".stravinsky",
    }

    def __init__(self, project_path: str, provider: EmbeddingProvider = "ollama"):
        self.project_path = Path(project_path).resolve()
        self.project_hash = hashlib.md5(str(self.project_path).encode()).hexdigest()[:12]

        # Initialize embedding provider
        self.provider_name = provider
        self.provider = get_embedding_provider(provider)

        # Store in user's home directory, separate by provider to avoid dimension mismatch
        self.db_path = Path.home() / ".stravinsky" / "vectordb" / f"{self.project_hash}_{provider}"
        self.db_path.mkdir(parents=True, exist_ok=True)

        # File lock for single-process access to ChromaDB (prevents corruption)
        self._lock_path = self.db_path / ".chromadb.lock"
        self._file_lock = None

        self._client = None
        self._collection = None

        # File watcher attributes
        self._watcher: "CodebaseFileWatcher | None" = None
        self._watcher_lock = threading.Lock()

    @property
    def file_lock(self):
        """Get or create the file lock for this database.

        Uses filelock to ensure single-process access to ChromaDB,
        preventing database corruption from concurrent writes.
        """
        if self._file_lock is None:
            filelock = get_filelock()
            # Timeout of 30 seconds - if lock can't be acquired, raise error
            self._file_lock = filelock.FileLock(str(self._lock_path), timeout=30)
        return self._file_lock

    @property
    def client(self):
        if self._client is None:
            chromadb = get_chromadb()
            # Acquire lock before creating client to prevent concurrent access
            try:
                self.file_lock.acquire()
                logger.debug(f"Acquired ChromaDB lock for {self.db_path}")
            except Exception as e:
                logger.warning(f"Could not acquire ChromaDB lock: {e}. Proceeding without lock.")
            self._client = chromadb.PersistentClient(path=str(self.db_path))
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="codebase", metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    async def check_embedding_service(self) -> bool:
        """Check if the embedding provider is available."""
        return await self.provider.check_available()

    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding vector for text using the configured provider."""
        return await self.provider.get_embedding(text)

    async def get_embeddings_batch(
        self, texts: list[str], max_concurrent: int = 10
    ) -> list[list[float]]:
        """Get embeddings for multiple texts with parallel execution.

        Uses asyncio.gather with semaphore-based concurrency control to avoid
        overwhelming the embedding service while maximizing throughput.

        Args:
            texts: List of text strings to embed
            max_concurrent: Maximum concurrent embedding requests (default: 10)

        Returns:
            List of embedding vectors in the same order as input texts.
        """
        import asyncio

        if not texts:
            return []

        # Use semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(max_concurrent)

        async def get_with_semaphore(text: str, index: int) -> tuple[int, list[float]]:
            async with semaphore:
                emb = await self.get_embedding(text)
                return (index, emb)

        # Launch all embedding requests concurrently (respecting semaphore)
        tasks = [get_with_semaphore(text, i) for i, text in enumerate(texts)]
        results = await asyncio.gather(*tasks)

        # Sort by original index to maintain order
        sorted_results = sorted(results, key=lambda x: x[0])
        return [emb for _, emb in sorted_results]

    def _chunk_file(self, file_path: Path) -> list[dict]:
        """Split a file into chunks with metadata.

        Uses AST-aware chunking for Python files to respect function/class
        boundaries. Falls back to line-based chunking for other languages.
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        lines = content.split("\n")
        if len(lines) < 5:  # Skip very small files
            return []

        rel_path = str(file_path.relative_to(self.project_path))
        language = file_path.suffix.lstrip(".")

        # Use AST-aware chunking for Python files
        if language == "py":
            chunks = self._chunk_python_ast(content, rel_path, language)
            if chunks:  # If AST parsing succeeded
                return chunks

        # Fallback: line-based chunking for other languages or if AST fails
        return self._chunk_by_lines(lines, rel_path, language)

    def _chunk_python_ast(self, content: str, rel_path: str, language: str) -> list[dict]:
        """Parse Python file and create chunks based on function/class boundaries.

        Each function, method, and class becomes its own chunk, preserving
        semantic boundaries for better embedding quality.
        """
        import ast

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []  # Fall back to line-based chunking

        lines = content.split("\n")
        chunks = []

        def get_docstring(node: ast.AST) -> str:
            """Extract docstring from a node if present."""
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and node.body
            ):
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    if isinstance(first.value.value, str):
                        return first.value.value
            return ""

        def get_decorators(
            node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
        ) -> list[str]:
            """Extract decorator names from a node."""
            decorators = []
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    decorators.append(f"@{dec.id}")
                elif isinstance(dec, ast.Attribute):
                    decorators.append(f"@{ast.unparse(dec)}")
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Name):
                        decorators.append(f"@{dec.func.id}")
                    elif isinstance(dec.func, ast.Attribute):
                        decorators.append(f"@{ast.unparse(dec.func)}")
            return decorators

        def get_base_classes(node: ast.ClassDef) -> list[str]:
            """Extract base class names from a class definition."""
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(ast.unparse(base))
                else:
                    bases.append(ast.unparse(base))
            return bases

        def get_return_type(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
            """Extract return type annotation from a function."""
            if node.returns:
                return ast.unparse(node.returns)
            return ""

        def get_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
            """Extract parameter signatures from a function."""
            params = []
            for arg in node.args.args:
                param = arg.arg
                if arg.annotation:
                    param += f": {ast.unparse(arg.annotation)}"
                params.append(param)
            return params

        def add_chunk(
            node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
            node_type: str,
            name: str,
            parent_class: str | None = None,
        ) -> None:
            """Add a chunk for a function/class node."""
            start_line = node.lineno
            end_line = node.end_lineno or start_line

            # Extract the source code for this node
            chunk_lines = lines[start_line - 1 : end_line]
            chunk_text = "\n".join(chunk_lines)
            content_hash = hashlib.md5(chunk_text.encode("utf-8")).hexdigest()[:12]

            # Skip very small chunks
            if len(chunk_lines) < 3:
                return

            # Build descriptive header
            docstring = get_docstring(node)
            if parent_class:
                header = f"File: {rel_path}\n{node_type}: {parent_class}.{name}\nLines: {start_line}-{end_line}"
            else:
                header = f"File: {rel_path}\n{node_type}: {name}\nLines: {start_line}-{end_line}"

            if docstring:
                header += f"\nDocstring: {docstring[:200]}..."

            document = f"{header}\n\n{chunk_text}"

            chunks.append(
                {
                    "id": f"{rel_path}:{start_line}-{end_line}:{content_hash}",
                    "document": document,
                    "metadata": {
                        "file_path": rel_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "language": language,
                        "node_type": node_type.lower(),
                        "name": f"{parent_class}.{name}" if parent_class else name,
                        # Structural metadata for filtering
                        "decorators": ",".join(get_decorators(node)),
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        # Class-specific metadata
                        "base_classes": ",".join(get_base_classes(node))
                        if isinstance(node, ast.ClassDef)
                        else "",
                        # Function-specific metadata
                        "return_type": get_return_type(node)
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                        else "",
                        "parameters": ",".join(get_parameters(node))
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                        else "",
                    },
                }
            )

        # Walk the AST and extract functions/classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                add_chunk(node, "Class", node.name)
                # Also add methods as separate chunks for granular search
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        add_chunk(item, "Method", item.name, parent_class=node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions (not methods)
                # Check if this function is inside a class body
                is_method = False
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ClassDef):
                        body = getattr(parent, "body", None)
                        if isinstance(body, list) and node in body:
                            is_method = True
                            break
                if not is_method:
                    add_chunk(node, "Function", node.name)

        # If we found no functions/classes, chunk module-level code
        if not chunks and len(lines) >= 5:
            # Add module-level chunk for imports and constants
            module_chunk = "\n".join(lines[: min(50, len(lines))])
            chunks.append(
                {
                    "id": f"{rel_path}:1-{min(50, len(lines))}",
                    "document": f"File: {rel_path}\nModule-level code\nLines: 1-{min(50, len(lines))}\n\n{module_chunk}",
                    "metadata": {
                        "file_path": rel_path,
                        "start_line": 1,
                        "end_line": min(50, len(lines)),
                        "language": language,
                        "node_type": "module",
                        "name": rel_path,
                    },
                }
            )

        return chunks

    def _chunk_by_lines(self, lines: list[str], rel_path: str, language: str) -> list[dict]:
        """Fallback line-based chunking with overlap."""
        chunks = []

        for i in range(0, len(lines), self.CHUNK_SIZE - self.CHUNK_OVERLAP):
            chunk_lines = lines[i : i + self.CHUNK_SIZE]
            if len(chunk_lines) < 5:  # Skip tiny trailing chunks
                continue

            chunk_text = "\n".join(chunk_lines)
            content_hash = hashlib.md5(chunk_text.encode("utf-8")).hexdigest()[:12]
            start_line = i + 1
            end_line = i + len(chunk_lines)

            # Create a searchable document with context
            document = f"File: {rel_path}\nLines: {start_line}-{end_line}\n\n{chunk_text}"

            chunks.append(
                {
                    "id": f"{rel_path}:{start_line}-{end_line}:{content_hash}",
                    "document": document,
                    "metadata": {
                        "file_path": rel_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "language": language,
                    },
                }
            )

        return chunks

    def _get_files_to_index(self) -> list[Path]:
        """Get all indexable files in the project."""
        files = []
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file():
                # Skip hidden files and directories
                if any(
                    part.startswith(".") for part in file_path.parts[len(self.project_path.parts) :]
                ):
                    if file_path.suffix not in {".md", ".txt"}:  # Allow .github docs
                        continue

                # Skip excluded directories
                if any(skip_dir in file_path.parts for skip_dir in self.SKIP_DIRS):
                    continue

                # Only include code files
                if file_path.suffix.lower() in self.CODE_EXTENSIONS:
                    files.append(file_path)

        return files

    async def index_codebase(self, force: bool = False) -> dict:
        """
        Index the entire codebase into the vector store.

        Args:
            force: If True, reindex everything. Otherwise, only index new/changed files.

        Returns:
            Statistics about the indexing operation.
        """
        import time

        # Start timing
        start_time = time.time()

        print(f"🔍 SEMANTIC-INDEX: {self.project_path}", file=sys.stderr)

        # Notify reindex start (non-blocking)
        notifier = None  # Initialize to avoid NameError in error handlers
        try:
            from mcp_bridge.notifications import get_notification_manager
            notifier = get_notification_manager()
            await notifier.notify_reindex_start(str(self.project_path))
        except Exception as e:
            logger.warning(f"Failed to send reindex start notification: {e}")

        try:
            if not await self.check_embedding_service():
                error_msg = "Embedding service not available"
                # Notify error
                try:
                    if notifier:
                        await notifier.notify_reindex_error(error_msg)
                except Exception as e:
                    logger.warning(f"Failed to send reindex error notification: {e}")
                return {"error": error_msg, "indexed": 0}

            # Get existing document IDs
            existing_ids = set()
            try:
                # Only fetch IDs to minimize overhead
                existing = self.collection.get(include=[])
                existing_ids = set(existing["ids"]) if existing["ids"] else set()
            except Exception:
                pass

            if force:
                # Clear existing collection
                try:
                    self.client.delete_collection("codebase")
                    self._collection = None
                    existing_ids = set()
                except Exception:
                    pass

            files = self._get_files_to_index()
            all_chunks = []
            current_chunk_ids = set()

            # Mark: Generate all chunks for current codebase
            for file_path in files:
                chunks = self._chunk_file(file_path)
                all_chunks.extend(chunks)
                for c in chunks:
                    current_chunk_ids.add(c["id"])

            # Sweep: Identify stale chunks to remove
            to_delete = existing_ids - current_chunk_ids

            # Identify new chunks to add
            to_add_ids = current_chunk_ids - existing_ids
            chunks_to_add = [c for c in all_chunks if c["id"] in to_add_ids]

            # Prune stale chunks
            if to_delete:
                print(f"  Pruning {len(to_delete)} stale chunks...", file=sys.stderr)
                self.collection.delete(ids=list(to_delete))

            if not chunks_to_add:
                stats = {
                    "indexed": 0,
                    "pruned": len(to_delete),
                    "total_files": len(files),
                    "message": "No new chunks to index",
                    "time_taken": round(time.time() - start_time, 1),
                }
                # Notify completion
                try:
                    if notifier:
                        await notifier.notify_reindex_complete(stats)
                except Exception as e:
                    logger.warning(f"Failed to send reindex complete notification: {e}")
                return stats

            # Batch embed and store
            batch_size = 50
            total_indexed = 0

            for i in range(0, len(chunks_to_add), batch_size):
                batch = chunks_to_add[i : i + batch_size]

                documents = [c["document"] for c in batch]
                embeddings = await self.get_embeddings_batch(documents)

                self.collection.add(
                    ids=[c["id"] for c in batch],
                    documents=documents,
                    embeddings=embeddings,  # type: ignore[arg-type]
                    metadatas=[c["metadata"] for c in batch],
                )
                total_indexed += len(batch)
                print(f"  Indexed {total_indexed}/{len(chunks_to_add)} chunks...", file=sys.stderr)

            stats = {
                "indexed": total_indexed,
                "pruned": len(to_delete),
                "total_files": len(files),
                "db_path": str(self.db_path),
                "time_taken": round(time.time() - start_time, 1),
            }

            # Notify completion
            try:
                if notifier:
                    await notifier.notify_reindex_complete(stats)
            except Exception as e:
                logger.warning(f"Failed to send reindex complete notification: {e}")

            return stats

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Reindexing failed: {error_msg}")

            # Notify error
            try:
                if notifier:
                    await notifier.notify_reindex_error(error_msg)
            except Exception as notify_error:
                logger.warning(f"Failed to send reindex error notification: {notify_error}")

            raise

    async def search(
        self,
        query: str,
        n_results: int = 10,
        language: str | None = None,
        node_type: str | None = None,
        decorator: str | None = None,
        is_async: bool | None = None,
        base_class: str | None = None,
    ) -> list[dict]:
        """
        Search the codebase with a natural language query.

        Args:
            query: Natural language search query
            n_results: Maximum number of results to return
            language: Filter by language (e.g., "py", "ts", "js")
            node_type: Filter by node type (e.g., "function", "class", "method")
            decorator: Filter by decorator (e.g., "@property", "@staticmethod")
            is_async: Filter by async status (True = async only, False = sync only)
            base_class: Filter by base class (e.g., "BaseClass")

        Returns:
            List of matching code chunks with metadata.
        """
        filters = []
        if language:
            filters.append(f"language={language}")
        if node_type:
            filters.append(f"node_type={node_type}")
        if decorator:
            filters.append(f"decorator={decorator}")
        if is_async is not None:
            filters.append(f"is_async={is_async}")
        if base_class:
            filters.append(f"base_class={base_class}")
        filter_str = f" [{', '.join(filters)}]" if filters else ""
        print(f"🔎 SEMANTIC-SEARCH: '{query[:50]}...'{filter_str}", file=sys.stderr)

        if not await self.check_embedding_service():
            return [{"error": "Embedding service not available"}]

        # Check if collection has documents
        try:
            count = self.collection.count()
            if count == 0:
                return [{"error": "No documents indexed", "hint": "Run index_codebase first"}]
        except Exception as e:
            return [{"error": f"Collection error: {e}"}]

        # Get query embedding
        query_embedding = await self.get_embedding(query)

        # Build where clause for metadata filtering
        where_filters = []
        if language:
            where_filters.append({"language": language})
        if node_type:
            where_filters.append({"node_type": node_type.lower()})
        if decorator:
            # ChromaDB $like for substring match in comma-separated field
            # Use % wildcards for pattern matching
            where_filters.append({"decorators": {"$like": f"%{decorator}%"}})
        if is_async is not None:
            where_filters.append({"is_async": is_async})
        if base_class:
            # Use $like for substring match
            where_filters.append({"base_classes": {"$like": f"%{base_class}%"}})

        where_clause = None
        if len(where_filters) == 1:
            where_clause = where_filters[0]
        elif len(where_filters) > 1:
            where_clause = {"$and": where_filters}

        # Search with optional filtering
        query_kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": n_results,
            "include": ["documents", "metadatas", "distances"],
        }
        if where_clause:
            query_kwargs["where"] = where_clause

        results = self.collection.query(**query_kwargs)

        # Format results
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, _doc_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                document = results["documents"][0][i] if results["documents"] else ""

                # Extract just the code part (skip file/line header)
                code_lines = document.split("\n\n", 1)
                code = code_lines[1] if len(code_lines) > 1 else document

                formatted.append(
                    {
                        "file": metadata.get("file_path", "unknown"),
                        "lines": f"{metadata.get('start_line', '?')}-{metadata.get('end_line', '?')}",
                        "language": metadata.get("language", ""),
                        "relevance": round(1 - distance, 3),  # Convert distance to similarity
                        "code_preview": code[:500] + "..." if len(code) > 500 else code,
                    }
                )

        return formatted

    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        try:
            count = self.collection.count()
            return {
                "project_path": str(self.project_path),
                "db_path": str(self.db_path),
                "chunks_indexed": count,
                "embedding_provider": self.provider.name,
                "embedding_dimension": self.provider.dimension,
            }
        except Exception as e:
            return {"error": str(e)}

    def start_watching(self, debounce_seconds: float = 2.0) -> "CodebaseFileWatcher":
        """Start watching the project directory for file changes.

        Args:
            debounce_seconds: Time to wait before reindexing after changes (default: 2.0s)

        Returns:
            The CodebaseFileWatcher instance
        """
        with self._watcher_lock:
            if self._watcher is None:
                # Avoid circular import by importing here
                self._watcher = CodebaseFileWatcher(
                    project_path=self.project_path,
                    store=self,
                    debounce_seconds=debounce_seconds,
                )
                self._watcher.start()
            else:
                if not self._watcher.is_running():
                    self._watcher.start()
                else:
                    logger.warning(f"Watcher for {self.project_path} is already running")
            return self._watcher

    def stop_watching(self) -> bool:
        """Stop watching the project directory.

        Returns:
            True if watcher was stopped, False if no watcher was active
        """
        with self._watcher_lock:
            if self._watcher is not None:
                self._watcher.stop()
                self._watcher = None
                return True
            return False

    def is_watching(self) -> bool:
        """Check if the project directory is being watched.

        Returns:
            True if watcher is active and running, False otherwise
        """
        with self._watcher_lock:
            if self._watcher is not None:
                return self._watcher.is_running()
            return False


# --- Module-level API for MCP tools ---

_stores: dict[str, CodebaseVectorStore] = {}
_stores_lock = threading.Lock()

# Module-level watcher management
_watchers: dict[str, "CodebaseFileWatcher"] = {}
_watchers_lock = threading.Lock()


def get_store(project_path: str, provider: EmbeddingProvider = "ollama") -> CodebaseVectorStore:
    """Get or create a vector store for a project.

    Note: Cache key includes provider to prevent cross-provider conflicts
    (different providers have different embedding dimensions).
    """
    path = str(Path(project_path).resolve())
    cache_key = f"{path}:{provider}"
    if cache_key not in _stores:
        with _stores_lock:
            # Double-check pattern to avoid race condition
            if cache_key not in _stores:
                _stores[cache_key] = CodebaseVectorStore(path, provider)
    return _stores[cache_key]


async def semantic_search(
    query: str,
    project_path: str = ".",
    n_results: int = 10,
    language: str | None = None,
    node_type: str | None = None,
    decorator: str | None = None,
    is_async: bool | None = None,
    base_class: str | None = None,
    provider: EmbeddingProvider = "ollama",
) -> str:
    """
    Search codebase with natural language query.

    Args:
        query: Natural language search query (e.g., "find authentication logic")
        project_path: Path to the project root
        n_results: Maximum number of results to return
        language: Filter by language (e.g., "py", "ts", "js")
        node_type: Filter by node type (e.g., "function", "class", "method")
        decorator: Filter by decorator (e.g., "@property", "@staticmethod")
        is_async: Filter by async status (True = async only, False = sync only)
        base_class: Filter by base class (e.g., "BaseClass")
        provider: Embedding provider (ollama, mxbai, gemini, openai, huggingface)

    Returns:
        Formatted search results with file paths and code snippets.
    """
    store = get_store(project_path, provider)
    results = await store.search(
        query,
        n_results,
        language,
        node_type,
        decorator=decorator,
        is_async=is_async,
        base_class=base_class,
    )

    if not results:
        return "No results found"

    if "error" in results[0]:
        return f"Error: {results[0]['error']}\nHint: {results[0].get('hint', 'Check Ollama is running')}"

    lines = [f"Found {len(results)} results for: '{query}'\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r['file']}:{r['lines']} (relevance: {r['relevance']})")
        lines.append(f"```{r['language']}")
        lines.append(r["code_preview"])
        lines.append("```\n")

    return "\n".join(lines)


async def hybrid_search(
    query: str,
    pattern: str | None = None,
    project_path: str = ".",
    n_results: int = 10,
    language: str | None = None,
    node_type: str | None = None,
    decorator: str | None = None,
    is_async: bool | None = None,
    base_class: str | None = None,
    provider: EmbeddingProvider = "ollama",
) -> str:
    """
    Hybrid search combining semantic similarity with structural AST matching.

    Performs semantic search first, then optionally filters/boosts results
    that also match an ast-grep structural pattern.

    Args:
        query: Natural language search query (e.g., "find authentication logic")
        pattern: Optional ast-grep pattern for structural matching (e.g., "def $FUNC($$$):")
        project_path: Path to the project root
        n_results: Maximum number of results to return
        language: Filter by language (e.g., "py", "ts", "js")
        node_type: Filter by node type (e.g., "function", "class", "method")
        decorator: Filter by decorator (e.g., "@property", "@staticmethod")
        is_async: Filter by async status (True = async only, False = sync only)
        base_class: Filter by base class (e.g., "BaseClass")
        provider: Embedding provider (ollama, gemini, openai)

    Returns:
        Formatted search results with relevance scores and structural match indicators.
    """
    from mcp_bridge.tools.code_search import ast_grep_search

    # Get semantic results (fetch more if we're going to filter)
    fetch_count = n_results * 2 if pattern else n_results
    semantic_result = await semantic_search(
        query=query,
        project_path=project_path,
        n_results=fetch_count,
        language=language,
        node_type=node_type,
        decorator=decorator,
        is_async=is_async,
        base_class=base_class,
        provider=provider,
    )

    if not pattern:
        return semantic_result

    if semantic_result.startswith("Error:") or semantic_result == "No results found":
        return semantic_result

    # Get structural matches from ast-grep
    ast_result = await ast_grep_search(
        pattern=pattern,
        directory=project_path,
        language=language or "",
    )

    # Extract file paths from ast-grep results
    ast_files: set[str] = set()
    if ast_result and not ast_result.startswith("Error:") and ast_result != "No matches found":
        for line in ast_result.split("\n"):
            if line.startswith("- "):
                # Format: "- file.py:123"
                file_part = line[2:].split(":")[0]
                ast_files.add(file_part)

    if not ast_files:
        # No structural matches, return semantic results with note
        return f"{semantic_result}\n\n[Note: No structural matches for pattern '{pattern}']"

    # Parse semantic results and boost/annotate files that appear in both
    lines = []
    result_lines = semantic_result.split("\n")
    header = result_lines[0] if result_lines else ""
    lines.append(header.replace("results for:", "hybrid results for:"))
    lines.append(f"[Structural pattern: {pattern}]\n")

    i = 1
    boosted_count = 0
    while i < len(result_lines):
        line = result_lines[i]
        if line and (line[0].isdigit() or line.startswith("```") or line.strip()):
            # Check if this is a result header line (e.g., "1. file.py:10-20")
            if line and line[0].isdigit() and "." in line:
                file_part = line.split()[1].split(":")[0] if len(line.split()) > 1 else ""
                if file_part in ast_files:
                    lines.append(f"{line} 🎯 [structural match]")
                    boosted_count += 1
                else:
                    lines.append(line)
            else:
                lines.append(line)
        else:
            lines.append(line)
        i += 1

    lines.append(
        f"\n[{boosted_count}/{len(ast_files)} semantic results also match structural pattern]"
    )

    return "\n".join(lines)


async def index_codebase(
    project_path: str = ".",
    force: bool = False,
    provider: EmbeddingProvider = "ollama",
) -> str:
    """
    Index a codebase for semantic search.

    Args:
        project_path: Path to the project root
        force: If True, reindex everything. Otherwise, only new/changed files.
        provider: Embedding provider - ollama (local/free), mxbai (local/free),
                  gemini (cloud/OAuth), openai (cloud/OAuth), huggingface (cloud/token)

    Returns:
        Indexing statistics.
    """
    store = get_store(project_path, provider)
    stats = await store.index_codebase(force=force)

    if "error" in stats:
        return f"Error: {stats['error']}"

    return (
        f"Indexed {stats['indexed']} chunks from {stats['total_files']} files\n"
        f"Database: {stats.get('db_path', 'unknown')}\n"
        f"{stats.get('message', '')}"
    )


async def semantic_stats(
    project_path: str = ".",
    provider: EmbeddingProvider = "ollama",
) -> str:
    """
    Get statistics about the semantic search index.

    Args:
        project_path: Path to the project root
        provider: Embedding provider - ollama (local/free), mxbai (local/free),
                  gemini (cloud/OAuth), openai (cloud/OAuth), huggingface (cloud/token)

    Returns:
        Index statistics.
    """
    store = get_store(project_path, provider)
    stats = store.get_stats()

    if "error" in stats:
        return f"Error: {stats['error']}"

    return (
        f"Project: {stats['project_path']}\n"
        f"Database: {stats['db_path']}\n"
        f"Chunks indexed: {stats['chunks_indexed']}\n"
        f"Embedding provider: {stats['embedding_provider']} ({stats['embedding_dimension']} dims)"
    )


async def semantic_health(project_path: str = ".", provider: EmbeddingProvider = "ollama") -> str:
    """Check health of semantic search system."""
    store = get_store(project_path, provider)

    status = []

    # Check Provider
    try:
        is_avail = await store.check_embedding_service()
        status.append(
            f"Provider ({store.provider.name}): {'✅ Online' if is_avail else '❌ Offline'}"
        )
    except Exception as e:
        status.append(f"Provider ({store.provider.name}): ❌ Error - {e}")

    # Check DB
    try:
        count = store.collection.count()
        status.append(f"Vector DB: ✅ Online ({count} documents)")
    except Exception as e:
        status.append(f"Vector DB: ❌ Error - {e}")

    return "\n".join(status)


# ========================
# FILE WATCHER MANAGEMENT
# ========================


def start_file_watcher(
    project_path: str,
    provider: EmbeddingProvider = "ollama",
    debounce_seconds: float = 2.0,
) -> "CodebaseFileWatcher":
    """Start watching a project directory for file changes.

    Args:
        project_path: Path to the project root
        provider: Embedding provider to use for reindexing
        debounce_seconds: Time to wait before reindexing after changes

    Returns:
        The started CodebaseFileWatcher instance
    """
    path = str(Path(project_path).resolve())
    with _watchers_lock:
        if path not in _watchers:
            store = get_store(project_path, provider)

            # Check if index exists
            try:
                stats = store.get_stats()
                chunks_indexed = stats.get("chunks_indexed", 0)
                if chunks_indexed == 0:
                    logger.warning(
                        f"No index found for {path}. Consider running semantic_index() "
                        f"first for better performance. FileWatcher will still monitor changes."
                    )
            except Exception as e:
                logger.debug(f"Could not check index status: {e}")

            watcher = store.start_watching(debounce_seconds=debounce_seconds)
            _watchers[path] = watcher
        else:
            watcher = _watchers[path]
            if not watcher.is_running():
                watcher.start()
        return _watchers[path]


def stop_file_watcher(project_path: str) -> bool:
    """Stop watching a project directory.

    Args:
        project_path: Path to the project root

    Returns:
        True if watcher was stopped, False if no watcher was active
    """
    path = str(Path(project_path).resolve())
    with _watchers_lock:
        if path in _watchers:
            watcher = _watchers[path]
            watcher.stop()
            del _watchers[path]
            return True
        return False


def get_file_watcher(project_path: str) -> "CodebaseFileWatcher | None":
    """Get an active file watcher for a project.

    Args:
        project_path: Path to the project root

    Returns:
        The CodebaseFileWatcher if active, None otherwise
    """
    path = str(Path(project_path).resolve())
    with _watchers_lock:
        watcher = _watchers.get(path)
        if watcher is not None and watcher.is_running():
            return watcher
        return None


def list_file_watchers() -> list[dict]:
    """List all active file watchers.

    Returns:
        List of dicts with watcher info (project_path, debounce_seconds, provider, status)
    """
    with _watchers_lock:
        watchers_info = []
        for path, watcher in _watchers.items():
            watchers_info.append(
                {
                    "project_path": path,
                    "debounce_seconds": watcher.debounce_seconds,
                    "provider": watcher.store.provider_name,
                    "status": "running" if watcher.is_running() else "stopped",
                }
            )
        return watchers_info


# ========================
# MULTI-QUERY EXPANSION & DECOMPOSITION
# ========================


async def _expand_query_with_llm(query: str, num_variations: int = 3) -> list[str]:
    """
    Use LLM to rephrase a query into multiple semantic variations.

    For example: "database connection" -> ["SQLAlchemy engine setup",
    "connect to postgres", "db session management"]

    Args:
        query: Original search query
        num_variations: Number of variations to generate (default: 3)

    Returns:
        List of query variations including the original
    """
    from mcp_bridge.tools.model_invoke import invoke_gemini

    prompt = f"""You are a code search query expander. Given a search query, generate {num_variations} alternative phrasings that would help find relevant code.

Original query: "{query}"

Generate {num_variations} alternative queries that:
1. Use different technical terminology (e.g., "database" -> "SQLAlchemy", "ORM", "connection pool")
2. Reference specific implementations or patterns
3. Include related concepts that might appear in code

Return ONLY the alternative queries, one per line. No numbering, no explanations.
Example output for "database connection":
SQLAlchemy engine configuration
postgres connection setup
db session factory pattern"""

    try:
        result = await invoke_gemini(
            token_store=TokenStore(),
            prompt=prompt,
            model="gemini-2.0-flash",
            temperature=0.7,
            max_tokens=200,
        )

        # Parse variations from response
        variations = [line.strip() for line in result.strip().split("\n") if line.strip()]
        # Always include original query first
        all_queries = [query] + variations[:num_variations]
        return all_queries

    except Exception as e:
        logger.warning(f"Query expansion failed: {e}, using original query only")
        return [query]


async def _decompose_query_with_llm(query: str) -> list[str]:
    """
    Break a complex query into smaller, focused sub-questions.

    For example: "Initialize the DB and then create a user model" ->
    ["database initialization", "user model definition"]

    Args:
        query: Complex search query

    Returns:
        List of sub-queries, or [query] if decomposition not needed
    """
    from mcp_bridge.tools.model_invoke import invoke_gemini

    prompt = f"""You are a code search query analyzer. Determine if this query should be broken into sub-queries.

Query: "{query}"

If the query contains multiple distinct concepts (connected by "and", "then", "also", etc.),
break it into separate focused sub-queries.

If the query is already focused on a single concept, return just that query.

Return ONLY the sub-queries, one per line. No numbering, no explanations.

Examples:
- "Initialize the DB and then create a user model" -> 
database initialization
user model definition

- "authentication logic" ->
authentication logic"""

    try:
        result = await invoke_gemini(
            token_store=TokenStore(),
            prompt=prompt,
            model="gemini-2.0-flash",
            temperature=0.3,  # Lower temperature for more consistent decomposition
            max_tokens=150,
        )

        # Parse sub-queries from response
        sub_queries = [line.strip() for line in result.strip().split("\n") if line.strip()]
        return sub_queries if sub_queries else [query]

    except Exception as e:
        logger.warning(f"Query decomposition failed: {e}, using original query")
        return [query]


def _aggregate_results(
    all_results: list[list[dict]],
    n_results: int = 10,
) -> list[dict]:
    """
    Aggregate and deduplicate results from multiple queries.

    Uses reciprocal rank fusion to combine relevance scores from different queries.

    Args:
        all_results: List of result lists from different queries
        n_results: Maximum number of results to return

    Returns:
        Deduplicated and re-ranked results
    """
    # Track seen files to avoid duplicates
    seen_files: dict[str, dict] = {}  # file:lines -> result with best score
    file_scores: dict[str, float] = {}  # file:lines -> aggregated score

    # Reciprocal Rank Fusion constant
    k = 60

    for query_idx, results in enumerate(all_results):
        for rank, result in enumerate(results):
            file_key = f"{result.get('file', '')}:{result.get('lines', '')}"

            # RRF score contribution
            rrf_score = 1 / (k + rank + 1)

            if file_key not in seen_files:
                seen_files[file_key] = result.copy()
                file_scores[file_key] = rrf_score
            else:
                # Aggregate scores
                file_scores[file_key] += rrf_score
                # Keep higher original relevance if available
                if result.get("relevance", 0) > seen_files[file_key].get("relevance", 0):
                    seen_files[file_key] = result.copy()

    # Sort by aggregated score and return top N
    sorted_keys = sorted(file_scores.keys(), key=lambda k: file_scores[k], reverse=True)

    aggregated = []
    for key in sorted_keys[:n_results]:
        result = seen_files[key]
        # Update relevance to reflect aggregated score (normalized)
        max_score = max(file_scores.values()) if file_scores else 1
        result["relevance"] = round(file_scores[key] / max_score, 3)
        aggregated.append(result)

    return aggregated


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

    Rephrases the query into multiple semantic variations, searches for each,
    and aggregates results using reciprocal rank fusion.

    Args:
        query: Natural language search query
        project_path: Path to the project root
        n_results: Maximum number of results to return
        num_expansions: Number of query variations to generate (default: 3)
        language: Filter by language (e.g., "py", "ts")
        node_type: Filter by node type (e.g., "function", "class")
        provider: Embedding provider

    Returns:
        Formatted search results with relevance scores.
    """
    import asyncio

    print(f"🔍 MULTI-QUERY: Expanding '{query[:50]}...'", file=sys.stderr)

    # Get query expansions
    expanded_queries = await _expand_query_with_llm(query, num_expansions)
    print(f"  Generated {len(expanded_queries)} query variations", file=sys.stderr)

    # Get store once
    store = get_store(project_path, provider)

    # Search with all queries in parallel
    async def search_single(q: str) -> list[dict]:
        return await store.search(
            q,
            n_results=n_results,  # Get full results for each query
            language=language,
            node_type=node_type,
        )

    all_results = await asyncio.gather(*[search_single(q) for q in expanded_queries])

    # Filter out error results
    valid_results = [r for r in all_results if r and "error" not in r[0]]

    if not valid_results:
        if all_results and all_results[0] and "error" in all_results[0][0]:
            return f"Error: {all_results[0][0]['error']}"
        return "No results found"

    # Aggregate results
    aggregated = _aggregate_results(valid_results, n_results)

    if not aggregated:
        return "No results found"

    # Format output
    lines = [f"Found {len(aggregated)} results for multi-query expansion of: '{query}'"]
    lines.append(
        f"[Expanded to: {', '.join(q[:30] + '...' if len(q) > 30 else q for q in expanded_queries)}]\n"
    )

    for i, r in enumerate(aggregated, 1):
        lines.append(f"{i}. {r['file']}:{r['lines']} (relevance: {r['relevance']})")
        lines.append(f"```{r.get('language', '')}")
        lines.append(r.get("code_preview", ""))
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

    Breaks multi-part queries like "Initialize the DB and create a user model"
    into separate searches, returning organized results for each part.

    Args:
        query: Complex search query (may contain multiple concepts)
        project_path: Path to the project root
        n_results: Maximum results per sub-query
        language: Filter by language
        node_type: Filter by node type
        provider: Embedding provider

    Returns:
        Formatted results organized by sub-question.
    """
    import asyncio

    print(f"🔍 DECOMPOSED-SEARCH: Analyzing '{query[:50]}...'", file=sys.stderr)

    # Decompose query
    sub_queries = await _decompose_query_with_llm(query)
    print(f"  Decomposed into {len(sub_queries)} sub-queries", file=sys.stderr)

    if len(sub_queries) == 1 and sub_queries[0] == query:
        # No decomposition needed, use regular search
        return await semantic_search(
            query=query,
            project_path=project_path,
            n_results=n_results,
            language=language,
            node_type=node_type,
            provider=provider,
        )

    # Get store once
    store = get_store(project_path, provider)

    # Search each sub-query in parallel
    async def search_sub(q: str) -> tuple[str, list[dict]]:
        results = await store.search(
            q,
            n_results=n_results // len(sub_queries) + 2,  # Distribute results
            language=language,
            node_type=node_type,
        )
        return (q, results)

    sub_results = await asyncio.gather(*[search_sub(q) for q in sub_queries])

    # Format output with sections for each sub-query
    lines = [f"Decomposed search for: '{query}'"]
    lines.append(f"[Split into {len(sub_queries)} sub-queries]\n")

    total_results = 0
    for sub_query, results in sub_results:
        lines.append(f"### {sub_query}")

        if not results or (results and "error" in results[0]):
            lines.append("  No results found\n")
            continue

        for i, r in enumerate(results[:5], 1):  # Limit per sub-query
            lines.append(f"  {i}. {r['file']}:{r['lines']} (relevance: {r['relevance']})")
            # Shorter preview for decomposed results
            preview = r.get("code_preview", "")[:200]
            if len(r.get("code_preview", "")) > 200:
                preview += "..."
            lines.append(f"     ```{r.get('language', '')}")
            lines.append(f"     {preview}")
            lines.append("     ```")
            total_results += 1
        lines.append("")

    lines.append(f"[Total: {total_results} results across {len(sub_queries)} sub-queries]")

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
    Unified enhanced search combining expansion and decomposition.

    Automatically selects the best strategy based on query complexity:
    - Simple queries: Multi-query expansion for better recall
    - Complex queries: Decomposition + expansion for comprehensive coverage

    Args:
        query: Search query (simple or complex)
        project_path: Path to the project root
        n_results: Maximum number of results
        mode: Search mode - "auto", "expand", "decompose", or "both"
        language: Filter by language
        node_type: Filter by node type
        provider: Embedding provider

    Returns:
        Formatted search results.
    """
    # Detect query complexity
    complex_indicators = [" and ", " then ", " also ", " with ", ", then", ". then", "; "]
    is_complex = any(ind in query.lower() for ind in complex_indicators)

    # Determine mode
    if mode == "auto":
        mode = "decompose" if is_complex else "expand"

    if mode == "decompose":
        return await decomposed_search(
            query=query,
            project_path=project_path,
            n_results=n_results,
            language=language,
            node_type=node_type,
            provider=provider,
        )
    elif mode == "expand":
        return await multi_query_search(
            query=query,
            project_path=project_path,
            n_results=n_results,
            language=language,
            node_type=node_type,
            provider=provider,
        )
    elif mode == "both":
        # Decompose first, then expand each sub-query
        sub_queries = await _decompose_query_with_llm(query)

        all_results: list[list[dict]] = []
        store = get_store(project_path, provider)

        for sub_q in sub_queries:
            # Expand each sub-query
            expanded = await _expand_query_with_llm(sub_q, num_variations=2)
            for exp_q in expanded:
                results = await store.search(
                    exp_q,
                    n_results=5,
                    language=language,
                    node_type=node_type,
                )
                if results and "error" not in results[0]:
                    all_results.append(results)

        aggregated = _aggregate_results(all_results, n_results)

        if not aggregated:
            return "No results found"

        lines = [f"Enhanced search (decompose+expand) for: '{query}'"]
        lines.append(f"[{len(sub_queries)} sub-queries × expansions]\n")

        for i, r in enumerate(aggregated, 1):
            lines.append(f"{i}. {r['file']}:{r['lines']} (relevance: {r['relevance']})")
            lines.append(f"```{r.get('language', '')}")
            lines.append(r.get("code_preview", ""))
            lines.append("```\n")

        return "\n".join(lines)

    else:
        return f"Unknown mode: {mode}. Use 'auto', 'expand', 'decompose', or 'both'"


# ========================
# FILE WATCHER IMPLEMENTATION
# ========================


class CodebaseFileWatcher:
    """Watch a project directory for file changes and trigger reindexing.

    Features:
    - Watches for file create, modify, delete, move events
    - Filters to .py files only
    - Skips hidden files and directories (., .git, __pycache__, venv, etc.)
    - Debounces rapid changes to batch them into a single reindex
    - Thread-safe with daemon threads for clean shutdown
    - Integrates with CodebaseVectorStore for incremental indexing
    """

    # Default debounce time in seconds
    DEFAULT_DEBOUNCE_SECONDS = 2.0

    def __init__(
        self,
        project_path: Path | str,
        store: CodebaseVectorStore,
        debounce_seconds: float = DEFAULT_DEBOUNCE_SECONDS,
    ):
        """Initialize the file watcher.

        Args:
            project_path: Path to the project root to watch
            store: CodebaseVectorStore instance for reindexing
            debounce_seconds: Time to wait before reindexing after changes (default: 2.0s)
        """
        self.project_path = Path(project_path).resolve()
        self.store = store
        self.debounce_seconds = debounce_seconds

        # Observer and handler for watchdog
        self._observer = None
        self._event_handler = None

        # Thread safety
        self._lock = threading.Lock()
        self._running = False

        # Debouncing
        self._pending_reindex_timer: threading.Timer | None = None
        self._pending_files: set[Path] = set()
        self._pending_lock = threading.Lock()

    def start(self) -> None:
        """Start watching the project directory.

        Creates and starts a watchdog observer in a daemon thread.
        """
        with self._lock:
            if self._running:
                logger.warning(f"Watcher for {self.project_path} is already running")
                return

            try:
                watchdog = get_watchdog()
                Observer = watchdog["Observer"]

                # Create event handler class and instantiate
                FileChangeHandler = _create_file_change_handler_class()
                self._event_handler = FileChangeHandler(
                    project_path=self.project_path,
                    watcher=self,
                )

                # Create and start observer (daemon mode for clean shutdown)
                self._observer = Observer()
                self._observer.daemon = True
                self._observer.schedule(
                    self._event_handler,
                    str(self.project_path),
                    recursive=True,
                )
                self._observer.start()
                self._running = True
                logger.info(f"File watcher started for {self.project_path}")

            except Exception as e:
                logger.error(f"Failed to start file watcher: {e}")
                self._running = False
                raise

    def stop(self) -> None:
        """Stop watching the project directory.

        Cancels any pending reindex timers and stops the observer.
        """
        with self._lock:
            # Cancel pending reindex
            if self._pending_reindex_timer is not None:
                self._pending_reindex_timer.cancel()
                self._pending_reindex_timer = None

            # Stop observer
            if self._observer is not None:
                self._observer.stop()
                self._observer.join(timeout=5)  # Wait up to 5 seconds for shutdown
                self._observer = None

            self._event_handler = None
            self._running = False
            logger.info(f"File watcher stopped for {self.project_path}")

    def is_running(self) -> bool:
        """Check if the watcher is currently running.

        Returns:
            True if watcher is active, False otherwise
        """
        with self._lock:
            return self._running and self._observer is not None and self._observer.is_alive()

    def _on_file_changed(self, file_path: Path) -> None:
        """Called when a file changes (internal use by _FileChangeHandler).

        Accumulates files and triggers debounced reindex.

        Args:
            file_path: Path to the changed file
        """
        with self._pending_lock:
            self._pending_files.add(file_path)

            # Cancel previous timer
            if self._pending_reindex_timer is not None:
                self._pending_reindex_timer.cancel()

            # Start new timer
            self._pending_reindex_timer = self._create_debounce_timer()
            self._pending_reindex_timer.start()

    def _create_debounce_timer(self) -> threading.Timer:
        """Create a new debounce timer for reindexing.

        Returns:
            A threading.Timer configured for debounce reindexing
        """
        return threading.Timer(
            self.debounce_seconds,
            self._trigger_reindex,
        )

    def _trigger_reindex(self) -> None:
        """Trigger reindexing of accumulated changed files.

        This is called after the debounce period expires. It performs an
        incremental reindex focusing on the changed files.
        """
        import asyncio

        with self._pending_lock:
            if not self._pending_files:
                self._pending_reindex_timer = None
                return

            files_to_index = list(self._pending_files)
            self._pending_files.clear()
            self._pending_reindex_timer = None

        # Run async reindex in a new event loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.store.index_codebase(force=False))
                logger.debug(f"Reindexed {len(files_to_index)} changed files")
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error during file watcher reindex: {e}")


def _create_file_change_handler_class():
    """Create FileChangeHandler class that inherits from FileSystemEventHandler.

    This is a factory function that creates the handler class dynamically
    after watchdog is imported, allowing for lazy loading.
    """
    watchdog = get_watchdog()
    FileSystemEventHandler = watchdog["FileSystemEventHandler"]

    class _FileChangeHandler(FileSystemEventHandler):
        """Watchdog event handler for file system changes.

        Detects file create, modify, delete, and move events, filters them,
        and notifies the watcher of relevant changes.
        """

        def __init__(self, project_path: Path, watcher: CodebaseFileWatcher):
            """Initialize the event handler.

            Args:
                project_path: Root path of the project being watched
                watcher: CodebaseFileWatcher instance to notify
            """
            super().__init__()
            self.project_path = project_path
            self.watcher = watcher

        def on_created(self, event) -> None:
            """Called when a file is created."""
            if not event.is_directory and self._should_index_file(event.src_path):
                logger.debug(f"File created: {event.src_path}")
                self.watcher._on_file_changed(Path(event.src_path))

        def on_modified(self, event) -> None:
            """Called when a file is modified."""
            if not event.is_directory and self._should_index_file(event.src_path):
                logger.debug(f"File modified: {event.src_path}")
                self.watcher._on_file_changed(Path(event.src_path))

        def on_deleted(self, event) -> None:
            """Called when a file is deleted."""
            if not event.is_directory and self._should_index_file(event.src_path):
                logger.debug(f"File deleted: {event.src_path}")
                self.watcher._on_file_changed(Path(event.src_path))

        def on_moved(self, event) -> None:
            """Called when a file is moved."""
            if not event.is_directory:
                # Check destination path
                if self._should_index_file(event.dest_path):
                    logger.debug(f"File moved: {event.src_path} -> {event.dest_path}")
                    self.watcher._on_file_changed(Path(event.dest_path))
                # Also check source path (for deletion case)
                elif self._should_index_file(event.src_path):
                    logger.debug(f"File moved out: {event.src_path}")
                    self.watcher._on_file_changed(Path(event.src_path))

        def _should_index_file(self, file_path: str) -> bool:
            """Check if a file should trigger reindexing.

            Filters based on:
            - File extension (.py only)
            - Hidden files and directories (starting with .)
            - Skip directories (venv, __pycache__, .git, node_modules, etc.)

            Args:
                file_path: Path to the file to check

            Returns:
                True if file should trigger reindexing, False otherwise
            """
            path = Path(file_path)

            # Only .py files
            if path.suffix != ".py":
                return False

            # Skip hidden files
            if path.name.startswith("."):
                return False

            # Check for skip directories in the path
            for part in path.parts:
                if part.startswith("."):  # Hidden directories like .git, .venv
                    return False
                if part in {"__pycache__", "venv", "env", "node_modules"}:
                    return False

            # File is within project (resolve both paths to handle symlinks)
            try:
                path.resolve().relative_to(self.project_path)
                return True
            except ValueError:
                # File is outside project
                return False

    return _FileChangeHandler
