package users

// User is one account as the users API returns it.
type User struct {
	ID    string `json:"id"`
	Email string `json:"email"`
}

// BaseURL is the users API root.
const BaseURL = "https://api.example.com"
