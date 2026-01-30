// MongoDB Permissions Fix Script
// 
// Run this script using mongosh with admin privileges:
// mongosh "mongodb://admin_user:admin_password@51.84.228.85:27017/admin" fix_mongodb_permissions.js
//
// Or connect first, then load this file:
// mongosh "mongodb://admin_user:admin_password@51.84.228.85:27017/admin"
// load('fix_mongodb_permissions.js')

print("Fixing MongoDB permissions for 'moniqo' user...");
print("");

// Switch to admin database
db = db.getSiblingDB('admin');

const username = "moniqo";
const databases = [
  "moniqo_dev_demo",
  "moniqo_dev_real", 
  "moniqo_dev"
];

// Check if user exists
const userInfo = db.getUser(username);
if (!userInfo) {
  print(`User '${username}' not found. Creating user with permissions...`);
  
  // Create user with permissions
  db.createUser({
    user: username,
    pwd: "Kbk6BoNQRwfbIOWGew!JlJMI8XubGo?N",
    roles: databases.map(dbName => ({ role: "readWrite", db: dbName }))
  });
  
  print(`✅ Created user '${username}' with readWrite permissions on:`);
  databases.forEach(dbName => print(`   - ${dbName}`));
} else {
  print(`User '${username}' exists. Granting additional permissions...`);
  
  // Grant permissions on each database
  databases.forEach(dbName => {
    try {
      db.grantRolesToUser(username, [{ role: "readWrite", db: dbName }]);
      print(`✅ Granted readWrite permission on '${dbName}'`);
    } catch (e) {
      if (e.code === 11) {
        // Role already exists
        print(`ℹ️  User already has readWrite permission on '${dbName}'`);
      } else {
        print(`⚠️  Error granting permission on '${dbName}': ${e.message}`);
      }
    }
  });
}

// Verify permissions
print("");
print("Verifying user permissions...");
const finalUserInfo = db.getUser(username);
if (finalUserInfo) {
  print(`\nCurrent roles for user '${username}':`);
  finalUserInfo.roles.forEach(role => {
    print(`  - ${role.role} on ${role.db}`);
  });
} else {
  print(`❌ User '${username}' not found after setup`);
}

print("");
print("✅ Permissions setup complete!");
