// root.go — Cobra root command with version info and shared config loading
package cmd

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"
	"github.com/tranhoangtu-it/agentlens/cli/internal/api"
)

const version = "0.1.0"

// Config holds the persisted user configuration.
type Config struct {
	Endpoint string `json:"endpoint"`
	APIKey   string `json:"api_key"`
}

var rootCmd = &cobra.Command{
	Use:     "agentlens",
	Short:   "AgentLens CLI — inspect and manage AI agent traces",
	Version: version,
}

// Execute is the entry point called from main.go.
func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func init() {
	rootCmd.AddCommand(tracesCmd)
	rootCmd.AddCommand(pushCmd)
	rootCmd.AddCommand(configCmd)
}

// configPath returns the path to ~/.agentlens/config.json.
func configPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", fmt.Errorf("resolving home directory: %w", err)
	}
	return filepath.Join(home, ".agentlens", "config.json"), nil
}

// loadConfig reads the config file; returns zero-value Config on missing file.
func loadConfig() (Config, error) {
	path, err := configPath()
	if err != nil {
		return Config{}, err
	}

	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return Config{}, nil
	}
	if err != nil {
		return Config{}, fmt.Errorf("reading config: %w", err)
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return Config{}, fmt.Errorf("parsing config: %w", err)
	}
	return cfg, nil
}

// saveConfig writes cfg to ~/.agentlens/config.json, creating the dir if needed.
func saveConfig(cfg Config) error {
	path, err := configPath()
	if err != nil {
		return err
	}

	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return fmt.Errorf("creating config directory: %w", err)
	}

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return fmt.Errorf("serialising config: %w", err)
	}

	if err := os.WriteFile(path, data, 0600); err != nil {
		return fmt.Errorf("writing config: %w", err)
	}
	return nil
}

// newClient builds an API client from stored config, validating endpoint presence.
func newClient() (*api.Client, error) {
	cfg, err := loadConfig()
	if err != nil {
		return nil, err
	}
	if cfg.Endpoint == "" {
		return nil, fmt.Errorf("no endpoint configured — run: agentlens config set endpoint <url>")
	}
	return api.NewClient(cfg.Endpoint, cfg.APIKey), nil
}
