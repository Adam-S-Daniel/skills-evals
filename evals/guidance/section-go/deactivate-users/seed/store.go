package users

import (
	"context"
	"errors"
)

// ErrNotFound is returned when no user has the given ID.
var ErrNotFound = errors.New("user not found")

// Store keeps users in memory. The service owns one for its whole life.
type Store struct {
	byID map[string]User
}

// NewStore returns an empty Store.
func NewStore() *Store { return &Store{byID: map[string]User{}} }

// Get returns the user with the given ID, or ErrNotFound.
func (s *Store) Get(ctx context.Context, id string) (User, error) {
	if err := ctx.Err(); err != nil {
		return User{}, err
	}
	u, ok := s.byID[id]
	if !ok {
		return User{}, ErrNotFound
	}
	return u, nil
}

// Save inserts or replaces a user.
func (s *Store) Save(ctx context.Context, u User) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	s.byID[u.ID] = u
	return nil
}

// List returns every user.
func (s *Store) List(ctx context.Context) ([]User, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	out := make([]User, 0, len(s.byID))
	for _, u := range s.byID {
		out = append(out, u)
	}
	return out, nil
}

// Delete removes a user.
func (s *Store) Delete(ctx context.Context, id string) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	delete(s.byID, id)
	return nil
}

// Close releases the store.
func (s *Store) Close() error { return nil }
