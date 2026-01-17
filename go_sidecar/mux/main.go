package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/gorilla/websocket"
)

var (
	socketPath = flag.String("socket", "/tmp/stravinsky.sock", "Path to Unix socket for agent input")
	httpAddr   = flag.String("http", ":42000", "Address for HTTP/WebSocket server")
	upgrader   = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true }, // Allow all origins for local dev
	}
)

// Message represents a log line or event from an agent
type Message struct {
	AgentID   string    `json:"agent_id"`
	Type      string    `json:"type"` // stdout, stderr, event
	Content   string    `json:"content"`
	Timestamp time.Time `json:"timestamp"`
}

// Hub maintains the set of active WebSocket clients and broadcasts messages
type Hub struct {
	clients    map[*websocket.Conn]bool
	broadcast  chan Message
	register   chan *websocket.Conn
	unregister chan *websocket.Conn
	mutex      sync.Mutex
}

func newHub() *Hub {
	return &Hub{
		clients:    make(map[*websocket.Conn]bool),
		broadcast:  make(chan Message, 256), // Buffer slightly
		register:   make(chan *websocket.Conn),
		unregister: make(chan *websocket.Conn),
	}
}

func (h *Hub) run() {
	for {
		select {
		case client := <-h.register:
			h.mutex.Lock()
			h.clients[client] = true
			h.mutex.Unlock()
			log.Println("New WebSocket client connected")

		case client := <-h.unregister:
			h.mutex.Lock()
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				client.Close()
			}
			h.mutex.Unlock()
			log.Println("WebSocket client disconnected")

		case msg := <-h.broadcast:
			h.mutex.Lock()
			for client := range h.clients {
				err := client.WriteJSON(msg)
				if err != nil {
					log.Printf("WS write error: %v", err)
					client.Close()
					delete(h.clients, client)
				}
			}
			h.mutex.Unlock()
		}
	}
}

func handleUnixConnection(conn net.Conn, hub *Hub) {
	defer conn.Close()
	scanner := bufio.NewScanner(conn)
	for scanner.Scan() {
		line := scanner.Bytes()
		var msg Message
		if err := json.Unmarshal(line, &msg); err != nil {
			// If not JSON, wrap it as raw stdout
			msg = Message{
				AgentID:   "system",
				Type:      "raw",
				Content:   string(line),
				Timestamp: time.Now(),
			}
		}
		if msg.Timestamp.IsZero() {
			msg.Timestamp = time.Now()
		}
		hub.broadcast <- msg
	}
}

func main() {
	flag.Parse()

	// Setup Hub
	hub := newHub()
	go hub.run()

	// cleanup old socket
	os.Remove(*socketPath)

	// Setup Unix Listener (Input from Agents)
	listener, err := net.Listen("unix", *socketPath)
	if err != nil {
		log.Fatalf("Failed to listen on unix socket: %v", err)
	}
	defer listener.Close()
	
	// Set socket permissions so Python process can write
	if err := os.Chmod(*socketPath, 0777); err != nil {
		log.Printf("Failed to set socket permissions: %v", err)
	}

	// Handle Unix connections in background
	go func() {
		log.Printf("Listening for agents on %s", *socketPath)
		for {
			conn, err := listener.Accept()
			if err != nil {
				log.Printf("Accept error: %v", err)
				continue
			}
			go handleUnixConnection(conn, hub)
		}
	}()

	// Setup HTTP/WS Server (Output to Dashboard)
	http.HandleFunc("/ws", func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			log.Println("Upgrade error:", err)
			return
		}
		hub.register <- conn
	})
	
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})

	server := &http.Server{
		Addr:    *httpAddr,
		Handler: nil,
	}

	go func() {
		log.Printf("Dashboard server listening on %s", *httpAddr)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("HTTP server error: %v", err)
		}
	}()

	// Wait for interrupt
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	<-stop

	log.Println("Shutting down...")
	os.Remove(*socketPath)
}
