#!/bin/bash
set -eux

# Install Nginx according to the available package manager.
if command -v dnf >/dev/null 2>&1; then
    dnf install -y nginx
elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y nginx
else
    echo "No supported package manager found" >&2
    exit 1
fi

# Select the default Nginx web directory.
if [ -d /usr/share/nginx/html ]; then
    WEB_ROOT=/usr/share/nginx/html
else
    WEB_ROOT=/var/www/html
fi

# Create the page served by Nginx.
cat > "$WEB_ROOT/index.html" <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Day 25 - AWS EC2</title>
</head>
<body>
    <h1>Hello from AWS EC2</h1>
    <p>Day 25 - DevOps Winter Arc</p>
</body>
</html>
EOF

# Enable Nginx at startup and start it now.
systemctl enable --now nginx
