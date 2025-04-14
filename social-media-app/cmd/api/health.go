package main

import "net/http"

// `curl http://localhost:8080/v1/health` -> output `ok`

func (app *Application) healthCheckHandler(
	w http.ResponseWriter, r *http.Request,
) {
	w.Write([]byte("ok"))

	//
}
