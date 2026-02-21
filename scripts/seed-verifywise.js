#!/usr/bin/env node
// seed-verifywise.js — Idempotently create the default organization and admin user.
// Run after `npm run migrate-db` in verifywise/Servers.
// Usage: node scripts/seed-verifywise.js [--servers-dir <path>]
//
// Admin credentials after seeding:
//   Email:    verifywise@email.com
//   Password: MyJH4rTm!@.45L0wm

"use strict";

const path = require("path");

// Allow overriding the Servers dir so bcrypt/pg can be required from there
const args = process.argv.slice(2);
let serversDir = path.resolve(__dirname, "../verifywise/Servers");
for (let i = 0; i < args.length; i++) {
  if (args[i] === "--servers-dir" && args[i + 1]) {
    serversDir = path.resolve(args[i + 1]);
  }
}

// Both pg and bcrypt live in Servers/node_modules (not installed globally)
const bcrypt = require(path.join(serversDir, "node_modules/bcrypt"));
const { Client } = require(path.join(serversDir, "node_modules/pg"));

const DB = {
  host: process.env.DB_HOST || "localhost",
  port: parseInt(process.env.DB_PORT || "5432", 10),
  database: process.env.DB_NAME || "verifywise",
  user: process.env.DB_USER || "postgres",
  password: process.env.DB_PASSWORD || "test",
};

const ADMIN_EMAIL = "verifywise@email.com";
const ADMIN_PASSWORD = "MyJH4rTm!@.45L0wm";

async function seed() {
  const db = new Client(DB);
  await db.connect();

  try {
    // 1. Ensure default organization exists (id=1)
    await db.query(`
      INSERT INTO organizations (name, onboarding_status, created_at, updated_at)
      VALUES ('VerifyWise', 'completed', NOW(), NOW())
      ON CONFLICT DO NOTHING;
    `);
    const orgRes = await db.query("SELECT id FROM organizations ORDER BY id LIMIT 1;");
    const orgId = orgRes.rows[0]?.id;
    if (!orgId) throw new Error("Could not create or find organization");
    console.log(`Organization id=${orgId} OK`);

    // 2. Ensure admin user exists
    const existing = await db.query(
      "SELECT id FROM users WHERE email = $1;",
      [ADMIN_EMAIL]
    );
    if (existing.rows.length > 0) {
      console.log(`Admin user '${ADMIN_EMAIL}' already exists (id=${existing.rows[0].id})`);
      return;
    }

    const hash = await bcrypt.hash(ADMIN_PASSWORD, 10);
    const res = await db.query(
      `INSERT INTO users
         (name, surname, email, password_hash, role_id, created_at, last_login, is_demo, organization_id)
       VALUES ($1, $2, $3, $4, $5, NOW(), NOW(), false, $6)
       RETURNING id;`,
      ["VerifyWise", "Admin", ADMIN_EMAIL, hash, 1, orgId]
    );
    console.log(`Admin user '${ADMIN_EMAIL}' created (id=${res.rows[0].id})`);
  } finally {
    await db.end();
  }
}

seed().catch((err) => {
  console.error("Seed failed:", err.message);
  process.exit(1);
});
