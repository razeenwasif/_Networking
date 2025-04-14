package main

import (
	"log"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"github.com/razeenwasif/social-media-app/internal/store"
)

// application interface (dependencies)
type Application struct {
	serverConfig ServerConfig
	store        store.Storage
}

// Configurations
type ServerConfig struct {
	address string
	db      dbConfig
}

// database configurations
type dbConfig struct {
	address            string
	maxOpenConnections int
	maxIdleConnections int
	maxIdleTime        string
}

func (app *Application) mount() http.Handler {
	r := chi.NewRouter()

	// A good base middleware stack for REST API
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)

	// set a timeout value on the request context,
	// that will signal through cxt.Done() that the
	// request has timed out and further processing
	// should be stopped
	r.Use(middleware.Timeout(60 * time.Second))

	// Handler for endpoints grouping
	r.Route("/v1", func(r chi.Router) {
		r.Get("/health", app.healthCheckHandler)
	})

	// posts

	// users

	// auth

	return r
}

// method to boot up http server
func (app *Application) run(mux http.Handler) error {
	server := &http.Server{
		Addr:    app.serverConfig.address,
		Handler: mux,
		// if server takes more than 30 sec to
		// write a response to a client, timeout.
		WriteTimeout: time.Second * 30,
		// if the client takes more than 10 seconds to
		// to read from the server, timeout.
		ReadTimeout: time.Second * 10,
		IdleTimeout: time.Minute,
	}

	// log and start the server
	log.Printf("Server listening on %s",
		app.serverConfig.address)
	return server.ListenAndServe()
}
