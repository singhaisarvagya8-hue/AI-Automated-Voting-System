# Voting System

This project is a Flask application with server-rendered HTML templates. The templates are the frontend; there is no separate npm frontend.

## MySQL setup (macOS)

Start MySQL if it is installed with Homebrew:

```bash
brew services start mysql
```

Create the database:

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS voting_system_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

Create a local environment file and set the password used by MySQL:

```bash
cp .env.example .env
```

Edit `.env` and replace `YOUR_MYSQL_PASSWORD` in `DATABASE_URL`. The application uses `mysql-connector-python` through the `mysql+mysqlconnector://` SQLAlchemy URL.

## Install and run

From the project directory:

```bash
./run.sh
# or: source venv/bin/activate && python app.py
```

Open <http://127.0.0.1:5001>.

The application creates its tables automatically when started. To load the supplied demo records after the tables exist:

```bash
mysql -u root -p voting_system_db < seed_data.sql
```

Demo accounts from `seed_data.sql` use password `password123`:

- Admin: `ADMIN001`
- Voter: `CS202601`
- Voter: `CS202602`

## Stop the application

Press `Control+C` in the terminal. To stop Homebrew MySQL:

```bash
brew services stop mysql
```
