import os
import subprocess
import json
import shutil
from typing import List, Optional, Dict, Any
from fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Calibre MCP Server")

# Configuration
CALIBRE_LIBRARY_PATH = os.environ.get("CALIBRE_LIBRARY_PATH")

def get_calibredb_cmd() -> List[str]:
    """Returns the base command for calibredb, including library path if set."""
    cmd = ["calibredb"]
    if CALIBRE_LIBRARY_PATH:
        cmd.extend(["--with-library", CALIBRE_LIBRARY_PATH])
    return cmd

def run_calibredb(args: List[str]) -> str:
    """Runs a calibredb command and returns the stdout."""
    cmd = get_calibredb_cmd() + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"calibredb command failed: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("calibredb executable not found. Please ensure Calibre is installed and in your PATH.")

def _search_books(query: str) -> List[Dict[str, Any]]:
    # Use 'list' command with --search and JSON output
    # Fields: id, title, authors
    args = [
        "list",
        "--search", query,
        "--for-machine",  # JSON output
        "--fields", "id,title,authors"
    ]
    
    try:
        output = run_calibredb(args)
        books = json.loads(output)
        return books
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse calibredb output.")
    except RuntimeError as e:
        return [{"error": str(e)}]

@mcp.tool()
def search_books(query: str) -> List[Dict[str, Any]]:
    """
    Search for books in the Calibre library.
    
    Args:
        query: The search query (e.g., title, author).
        
    Returns:
        A list of books matching the query.
    """
    return _search_books(query)

def _get_book_details(book_id: int) -> Dict[str, Any]:
    # calibredb list --search "id:123" --for-machine
    args = [
        "list",
        "--search", f"id:{book_id}",
        "--for-machine"
    ]
    
    try:
        output = run_calibredb(args)
        books = json.loads(output)
        if not books:
            return {"error": f"Book with ID {book_id} not found."}
        return books[0]
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_book_details(book_id: int) -> Dict[str, Any]:
    """
    Get metadata for a specific book.
    
    Args:
        book_id: The ID of the book.
        
    Returns:
        Metadata for the book.
    """
    return _get_book_details(book_id)

def _add_book(file_path: str) -> str:
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
        
    args = ["add", file_path]
    
    try:
        output = run_calibredb(args)
        # Output typically: "Added book ids: 123"
        return output.strip()
    except RuntimeError as e:
        return f"Error adding book: {str(e)}"

@mcp.tool()
def add_book(file_path: str) -> str:
    """
    Add a new book file to the library.
    
    Args:
        file_path: The absolute path to the book file.
        
    Returns:
        Success message with the new Book ID.
    """
    return _add_book(file_path)

def _convert_book(book_id: int, output_format: str) -> str:
    # 1. Find the book and its source file
    details = _get_book_details(book_id)
    if "error" in details:
        return details["error"]
    
    formats = details.get("formats", [])
    if not formats:
        return "Error: No source formats found for this book."
    
    # Pick the first available format as source
    # formats is a list of absolute paths in the library
    source_file = formats[0]
    
    # Create a temporary output path
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as tmp:
        output_file = tmp.name
        
    try:
        # 2. Run ebook-convert
        convert_cmd = ["ebook-convert", source_file, output_file]
        subprocess.run(convert_cmd, check=True, capture_output=True)
        
        # 3. Add the new format to the book
        # calibredb add_format id file
        add_fmt_args = ["add_format", str(book_id), output_file]
        run_calibredb(add_fmt_args)
        
        return f"Successfully converted book {book_id} to {output_format}."
        
    except subprocess.CalledProcessError as e:
        return f"Error converting book: {e.stderr if e.stderr else str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        # Cleanup temp file
        if os.path.exists(output_file):
            os.remove(output_file)

@mcp.tool()
def convert_book(book_id: int, output_format: str) -> str:
    """
    Convert a book to a new format.
    
    Args:
        book_id: The ID of the book to convert.
        output_format: The desired output format (e.g., 'mobi', 'epub').
        
    Returns:
        Status message.
    """
    return _convert_book(book_id, output_format)

def _delete_book(book_id: int) -> str:
    args = ["remove", str(book_id), "--permanent"]
    try:
        run_calibredb(args)
        return f"Successfully deleted book {book_id}."
    except RuntimeError as e:
        return f"Error deleting book: {str(e)}"

@mcp.tool()
def delete_book(book_id: int) -> str:
    """
    Delete a book from the library permanently.
    
    Args:
        book_id: The ID of the book to delete.
        
    Returns:
        Status message.
    """
    return _delete_book(book_id)

def _export_book(book_id: int, output_dir: str) -> str:
    if not os.path.exists(output_dir):
        return f"Error: Output directory {output_dir} does not exist."
        
    args = ["export", str(book_id), "--to-dir", output_dir]
    try:
        run_calibredb(args)
        return f"Successfully exported book {book_id} to {output_dir}."
    except RuntimeError as e:
        return f"Error exporting book: {str(e)}"

@mcp.tool()
def export_book(book_id: int, output_dir: str) -> str:
    """
    Export a book to a specific directory.
    
    Args:
        book_id: The ID of the book to export.
        output_dir: The destination directory.
        
    Returns:
        Status message.
    """
    return _export_book(book_id, output_dir)

def _update_book(
    book_id: int, 
    title: Optional[str] = None, 
    authors: Optional[str] = None,
    series: Optional[str] = None,
    series_index: Optional[float] = None,
    rating: Optional[int] = None,
    publisher: Optional[str] = None,
    pubdate: Optional[str] = None,
    comments: Optional[str] = None,
    languages: Optional[str] = None
) -> str:
    # calibredb set_metadata id --field title:"New Title" --field authors:"Author Name"
    args = ["set_metadata", str(book_id)]
    
    if title:
        args.extend(["--field", f"title:{title}"])
    if authors:
        args.extend(["--field", f"authors:{authors}"])
    if series:
        args.extend(["--field", f"series:{series}"])
    if series_index is not None:
        args.extend(["--field", f"series_index:{series_index}"])
    if rating is not None:
        args.extend(["--field", f"rating:{rating}"])
    if publisher:
        args.extend(["--field", f"publisher:{publisher}"])
    if pubdate:
        args.extend(["--field", f"pubdate:{pubdate}"])
    if comments:
        args.extend(["--field", f"comments:{comments}"])
    if languages:
        args.extend(["--field", f"languages:{languages}"])
        
    if len(args) == 2:
        return "No updates provided."
        
    try:
        run_calibredb(args)
        return f"Successfully updated metadata for book {book_id}."
    except RuntimeError as e:
        return f"Error updating book: {str(e)}"

@mcp.tool()
def update_book(
    book_id: int, 
    title: Optional[str] = None, 
    authors: Optional[str] = None,
    series: Optional[str] = None,
    series_index: Optional[float] = None,
    rating: Optional[int] = None,
    publisher: Optional[str] = None,
    pubdate: Optional[str] = None,
    comments: Optional[str] = None,
    languages: Optional[str] = None
) -> str:
    """
    Update book metadata.
    
    Args:
        book_id: The ID of the book.
        title: New title (optional).
        authors: New authors (optional, comma-separated).
        series: Series name (optional).
        series_index: Number in series (optional).
        rating: Rating 1-5 (optional).
        publisher: Publisher name (optional).
        pubdate: Publication date (optional).
        comments: Book description/comments (optional).
        languages: Comma-separated languages (optional).
        
    Returns:
        Status message.
    """
    return _update_book(
        book_id, title, authors, series, series_index, 
        rating, publisher, pubdate, comments, languages
    )

def _manage_tags(book_id: int, add_tags: Optional[List[str]] = None, remove_tags: Optional[List[str]] = None) -> str:
    # calibredb set_metadata id --field tags:+tag1,+tag2,-tag3
    if not add_tags and not remove_tags:
        return "No tags to add or remove."
        
    tags_arg = ""
    if add_tags:
        tags_arg += "+" + ",+".join(add_tags)
    if remove_tags:
        if tags_arg:
            tags_arg += ","
        tags_arg += "-" + ",-".join(remove_tags)
        
    args = ["set_metadata", str(book_id), "--field", f"tags:{tags_arg}"]
    
    try:
        run_calibredb(args)
        return f"Successfully updated tags for book {book_id}."
    except RuntimeError as e:
        return f"Error updating tags: {str(e)}"

@mcp.tool()
def manage_tags(book_id: int, add_tags: Optional[List[str]] = None, remove_tags: Optional[List[str]] = None) -> str:
    """
    Add or remove tags from a book.
    
    Args:
        book_id: The ID of the book.
        add_tags: List of tags to add.
        remove_tags: List of tags to remove.
        
    Returns:
        Status message.
    """
    return _manage_tags(book_id, add_tags, remove_tags)

def _set_cover(book_id: int, cover_path: str) -> str:
    if not os.path.exists(cover_path):
        return f"Error: Cover file not found at {cover_path}"
        
    args = ["set_metadata", str(book_id), "--cover", cover_path]
    
    try:
        run_calibredb(args)
        return f"Successfully set cover for book {book_id}."
    except RuntimeError as e:
        return f"Error setting cover: {str(e)}"

@mcp.tool()
def set_cover(book_id: int, cover_path: str) -> str:
    """
    Set the cover image for a book.
    
    Args:
        book_id: The ID of the book.
        cover_path: Absolute path to the image file.
        
    Returns:
        Status message.
    """
    return _set_cover(book_id, cover_path)

def _get_cover_path(book_id: int) -> str:
    details = _get_book_details(book_id)
    if "error" in details:
        return details["error"]
        
    # The 'cover' field in details usually contains the path to the cover file
    cover = details.get("cover")
    if not cover:
        return "Error: No cover found for this book."
    return cover

@mcp.tool()
def get_cover_path(book_id: int) -> str:
    """
    Get the local path to the book's cover image.
    
    Args:
        book_id: The ID of the book.
        
    Returns:
        Absolute path to the cover image.
    """
    return _get_cover_path(book_id)

def _read_book_content(book_id: int) -> str:
    # 1. Find source
    details = _get_book_details(book_id)
    if "error" in details:
        return details["error"]
    
    formats = details.get("formats", [])
    if not formats:
        return "Error: No formats found for this book."
        
    source_file = formats[0]
    
    # 2. Convert to TXT
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        output_file = tmp.name
        
    try:
        convert_cmd = ["ebook-convert", source_file, output_file]
        subprocess.run(convert_cmd, check=True, capture_output=True)
        
        # 3. Read content
        with open(output_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
            
        # Truncate if too large (e.g., 100KB) to avoid overwhelming the context
        MAX_CHARS = 100000
        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS] + "\n... [Content truncated]"
            
        return content
        
    except subprocess.CalledProcessError as e:
        return f"Error converting book to text: {e.stderr if e.stderr else str(e)}"
    except Exception as e:
        return f"Error reading book content: {str(e)}"
    finally:
        if os.path.exists(output_file):
            os.remove(output_file)

@mcp.tool()
def read_book_content(book_id: int) -> str:
    """
    Read the text content of a book.
    
    Args:
        book_id: The ID of the book.
        
    Returns:
        The text content of the book (truncated if very large).
    """
    return _read_book_content(book_id)

def _list_categories(category_type: str) -> List[str]:
    # calibredb list_categories -r tags
    args = ["list_categories", "-r", category_type, "--csv"]
    try:
        output = run_calibredb(args)
        # Output is CSV lines: tag_name,count,avg_rating...
        # We just want the names
        lines = output.strip().splitlines()
        categories = []
        for line in lines:
            if line:
                # Simple CSV parsing (assuming no commas in names for now, or just split by first comma)
                parts = line.split(",")
                if parts:
                    categories.append(parts[0].strip('"'))
        return categories
    except RuntimeError as e:
        return [f"Error: {str(e)}"]

@mcp.tool()
def list_categories(category_type: str) -> List[str]:
    """
    List available categories (tags, authors, series, etc.).
    
    Args:
        category_type: The type of category (e.g., 'tags', 'authors', 'series', 'publisher').
        
    Returns:
        List of category names.
    """
    return _list_categories(category_type)

def _check_library() -> str:
    args = ["check_library"]
    try:
        # check_library writes to stdout/stderr
        output = run_calibredb(args)
        return output
    except RuntimeError as e:
        return f"Error checking library: {str(e)}"

@mcp.tool()
def check_library() -> str:
    """
    Run a consistency check on the library database.
    
    Returns:
        The report from the check command.
    """
    return _check_library()

def _get_library_stats() -> Dict[str, Any]:
    # We can get stats by listing all and counting, or using list_categories for authors/tags count
    try:
        # Count books
        list_args = ["list", "--for-machine", "--fields", "id"]
        books_output = run_calibredb(list_args)
        books = json.loads(books_output)
        book_count = len(books)
        
        # Count authors
        authors = _list_categories("authors")
        author_count = len(authors)
        
        # Count tags
        tags = _list_categories("tags")
        tag_count = len(tags)
        
        return {
            "book_count": book_count,
            "author_count": author_count,
            "tag_count": tag_count
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_library_stats() -> Dict[str, Any]:
    """
    Get statistics about the library.
    
    Returns:
        Dictionary with counts of books, authors, and tags.
    """
    return _get_library_stats()

if __name__ == "__main__":
    mcp.run()
