#!/bin/bash

# Load environment variables
source .env

# Run the SQL script
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p 6543 -f scripts/seed.sql 