"""Legacy ingest-and-query command; importing it performs no work."""
if __package__:
    from .ingest import create_vector_db
    from .query import main
else:
    from ingest import create_vector_db
    from query import main

if __name__ == "__main__":
    create_vector_db()
    main()
