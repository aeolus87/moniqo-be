#!/bin/bash
# MongoDB Permissions Fix Script
# 
# This script grants readWrite permissions to the moniqo user on required databases.
# 
# Usage: Run this script with MongoDB admin credentials
# 
# You need to connect to MongoDB as an admin user first, then run these commands:
# 
# Option 1: Connect via mongosh and run commands manually
# mongosh "mongodb://admin_user:admin_password@51.84.228.85:27017/admin"
# 
# Then run the commands below (or copy-paste them)

echo "MongoDB Permissions Fix Commands"
echo "================================="
echo ""
echo "Connect to MongoDB as admin user:"
echo 'mongosh "mongodb://admin_user:admin_password@51.84.228.85:27017/admin"'
echo ""
echo "Then run these commands:"
echo ""
echo "# Grant readWrite permission on moniqo_dev_demo database"
echo 'db.grantRolesToUser("moniqo", [{ role: "readWrite", db: "moniqo_dev_demo" }])'
echo ""
echo "# Grant readWrite permission on moniqo_dev_real database"
echo 'db.grantRolesToUser("moniqo", [{ role: "readWrite", db: "moniqo_dev_real" }])'
echo ""
echo "# Grant readWrite permission on moniqo_dev database (for backward compatibility)"
echo 'db.grantRolesToUser("moniqo", [{ role: "readWrite", db: "moniqo_dev" }])'
echo ""
echo "# Verify permissions"
echo 'db.getUser("moniqo")'
echo ""
echo ""
echo "If the user doesn't exist, create it with:"
echo 'db.createUser({'
echo '  user: "moniqo",'
echo '  pwd: "Kbk6BoNQRwfbIOWGew!JlJMI8XubGo?N",'
echo '  roles: ['
echo '    { role: "readWrite", db: "moniqo_dev_demo" },'
echo '    { role: "readWrite", db: "moniqo_dev_real" },'
echo '    { role: "readWrite", db: "moniqo_dev" }'
echo '  ]'
echo '})'
