package main

import (
	"log"

	"github.com/razeenwasif/social-media-app/internal/db"
	"github.com/razeenwasif/social-media-app/internal/env"
	"github.com/razeenwasif/social-media-app/internal/store"
)

// run using `go run cmd/api/*.go` or `air`

// entry point of the application
func main() {
	// all dependencies go here
	// create the configuration
	serverConfig := ServerConfig{
		address: env.GetString("ADDR", ":8080"),
		db: dbConfig{
			address: env.GetString(
				"DB_ADDR",
				"postgres://admin:adminpassword@localhost/social-media-app?sslmode=disable",
			),
			maxOpenConnections: env.GetInt("DB_MAX_OPEN_CONNS", 30),
			maxIdleConnections: env.GetInt("DB_MAX_IDLE_CONNS", 30),
			maxIdleTime:        env.GetString("DB_MAX_IDLE_TIME", "15m"),
		},
	}

	db, err := db.New(
		serverConfig.db.address,
		serverConfig.db.maxOpenConnections,
		serverConfig.db.maxIdleConnections,
		serverConfig.db.maxIdleTime,
	)
	if err != nil {
		log.Panic(err)
	}

	defer db.Close()
	log.Println("database connection pool established")

	// create the store
	store := store.NewStorage(db)

	// create the app
	app := &Application{
		serverConfig: serverConfig,
		store:        store,
	}

	// start the server
	log.Printf("Starting the server on %s",
		serverConfig.address)

	mux := app.mount()

	log.Fatal(app.run(mux))
}
