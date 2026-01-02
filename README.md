# im_bored
For when you're bored

# Installation
`uv pip install -e .`

## Setting up Tailscale
- [Download and install Tailscale](https://tailscale.com/download) on the host machine that will be running the app.
    - Note: if running in WSL2, install/run Tailscale within WSL2.
- Start Tailscale on the host machine (`sudo tailscale up`)
- Install Tailscale on the client machine (e.g., your phone)
- Start the Flask app: `uv run imbored-web`.
- Open a browser on the client and connect to the `ip:port`, making sure to use the IP displayed in [the Tailscale dashboard](https://login.tailscale.com/admin/machines).
