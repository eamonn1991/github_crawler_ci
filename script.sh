source venv/bin/activate
pip install -r requirements.txt

# Initialize the database
python src/init_db.py

# Run the crawler (single fetch)
python src/crawler.py --mode single --batch-size 100 --batch-threshold 900 --keywords kokkos
# Run the crawler (pipeline fetch)
python src/crawler.py --mode pipeline --batch-size 100 --start-year 2025 --start-month 5 --batch-threshold 900 --sort-by stars

# Read data
python src/read_data.py

# Dump data
python src/db_dump_upload.py dump

# Upload data
python src/db_dump_upload.py upload --file db_dump_20250602_150000.csv

# Set up docker
# 1. Download Docker Desktop for Mac from the official website: https://docs.docker.com/desktop/install/mac-install/
# 2. Run the Docker Compose command to start the services 
docker compose up -d
# 3. Verify that the database is accessible by checking if it's running and listening on the correct port
docker ps
# 4. Verify we can connect to the database
docker-compose exec db psql -U edison -d star_crawler_edison -c "\l"
# 5. Stop the container
docker-compose down
# optional: stop and remove the containers
docker-compose down -v

# About the database
# Method 1: Using connection string
PGPASSWORD=postgres psql -h localhost -p 5432 -U edison -d star_crawler_edison
# 1. List all tables: 
\dt
# 2. Describe a table: 
\d repositories
# 3. Run SQL queries: 
SELECT * FROM repositories;
# 4. Count the number of rows in the repositories table:
SELECT COUNT(*) FROM repositories;
# 5. Quit: 
\q

# Verify no PostgreSQL processes are running:
ps aux | grep postgres
