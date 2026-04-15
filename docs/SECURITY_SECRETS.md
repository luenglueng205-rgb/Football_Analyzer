# Secrets Policy

## Rule

Never store secrets in git, source code, or shareable shell configs.

## Recommended local setup (macOS)

1. Put secrets into a dedicated file:

- `~/.zshrc.secrets`

2. Source it from `~/.zshrc`:

```sh
source "$HOME/.zshrc.secrets"
```

3. Ensure the secrets file is only readable by your user:

```sh
chmod 600 "$HOME/.zshrc.secrets"
```

## Rotation

If a key has ever appeared in plaintext in a file or chat, rotate it immediately on the provider side and update your local secret store.
