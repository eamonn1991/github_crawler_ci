from sqlalchemy import desc
from models import Repository, get_db

def get_most_starred_repos(limit: int = 10):
    """Get the repositories with the most stars"""
    db = next(get_db())
    try:
        repos = db.query(Repository)\
            .order_by(desc(Repository.star_count))\
            .limit(limit)\
            .all()
        
        print(f"\nTop {limit} Most Starred Repositories:")
        print("-" * 50)
        for repo in repos:
            print(f"Name: {repo.name}")
            print(f"Stars: {repo.star_count}")
            print(f"Last Updated: {repo.updated_at}")
            print("-" * 50)
        
        return repos
    finally:
        db.close()


if __name__ == "__main__":
    # Example usage
    print("Reading data from database...")

    # Get top 5 most starred repositories
    get_most_starred_repos(limit=5)
