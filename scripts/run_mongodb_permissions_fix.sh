#!/bin/bash
# MongoDB Permissions Fix - Ready to Run
#
# This script will fix MongoDB permissions for the moniqo user.
# You need to provide admin credentials when prompted.

set -e

echo "=========================================="
echo "MongoDB Permissions Fix Script"
echo "=========================================="
echo ""
echo "This script will grant readWrite permissions to the 'moniqo' user on:"
echo "  - moniqo_dev_demo"
echo "  - moniqo_dev_real"
echo "  - moniqo_dev"
echo ""
echo "You need MongoDB admin credentials to run this."
echo ""

# Prompt for admin credentials
read -p "Enter MongoDB admin username: " ADMIN_USER
read -sp "Enter MongoDB admin password: " ADMIN_PASS
echo ""
read -p "Enter MongoDB host (default: 51.84.228.85:27017): " MONGO_HOST
MONGO_HOST=${MONGO_HOST:-51.84.228.85:27017}

# URL encode the password (basic encoding for common characters)
ADMIN_PASS_ENCODED=$(echo "$ADMIN_PASS" | sed 's/!/%21/g' | sed 's/?/%3F/g' | sed 's/@/%40/g' | sed 's/#/%23/g' | sed 's/\$/%24/g' | sed 's/&/%26/g' | sed 's/\*/%2A/g' | sed 's/+/%2B/g' | sed 's/=/%3D/g')

MONGO_URL="mongodb://${ADMIN_USER}:${ADMIN_PASS_ENCODED}@${MONGO_HOST}/admin"

echo ""
echo "Connecting to MongoDB..."
echo ""

# Run the permissions fix commands
mongosh "$MONGO_URL" <<EOF
print("Fixing MongoDB permissions for 'moniqo' user...");
print("");

// Grant readWrite on moniqo_dev_demo
try {
  db.grantRolesToUser("moniqo", [{ role: "readWrite", db: "moniqo_dev_demo" }]);
  print("✅ Granted readWrite permission on 'moniqo_dev_demo'");
} catch (e) {
  if (e.code === 11) {
    print("ℹ️  User already has readWrite permission on 'moniqo_dev_demo'");
  } else {
    print("⚠️  Error: " + e.message);
  }
}

// Grant readWrite on moniqo_dev_real
try {
  db.grantRolesToUser("moniqo", [{ role: "readWrite", db: "moniqo_dev_real" }]);
  print("✅ Granted readWrite permission on 'moniqo_dev_real'");
} catch (e) {
  if (e.code === 11) {
    print("ℹ️  User already has readWrite permission on 'moniqo_dev_real'");
  } else {
    print("⚠️  Error: " + e.message);
  }
}

// Grant readWrite on moniqo_dev
try {
  db.grantRolesToUser("moniqo", [{ role: "readWrite", db: "moniqo_dev" }]);
  print("✅ Granted readWrite permission on 'moniqo_dev'");
} catch (e) {
  if (e.code === 11) {
    print("ℹ️  User already has readWrite permission on 'moniqo_dev'");
  } else {
    print("⚠️  Error: " + e.message);
  }
}

// Verify permissions
print("");
print("Verifying user permissions...");
const userInfo = db.getUser("moniqo");
if (userInfo) {
  print("\nCurrent roles for user 'moniqo':");
  userInfo.roles.forEach(role => {
    print("  - " + role.role + " on " + role.db);
  });
} else {
  print("❌ User 'moniqo' not found");
}

print("");
print("✅ Permissions setup complete!");
EOF

echo ""
echo "Done!"
