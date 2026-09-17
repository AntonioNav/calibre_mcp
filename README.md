# Calibre MCP Server

[English](README.md)

A Model Context Protocol (MCP) server that provides an interface to your local [Calibre](https://calibre-ebook.com/) library. This allows AI agents (like Claude or Cursor) to search, retrieve details, add, and convert books in your Calibre library.

## Features

- **Search Books**: Query your library by title, author, or other metadata.
- **Get Details**: Retrieve full metadata for specific books, including available formats and file paths.
- **Add Books**: Add new book files to your library from the local filesystem.
- **Convert Books**: Convert books between formats (e.g., EPUB to MOBI) using Calibre's `ebook-convert` tool.

## Prerequisites

- **Python 3.10+**
- **Calibre**: The `calibredb` and `ebook-convert` command-line tools must be installed and accessible in your system PATH.
  - On macOS, these are typically found in `/Applications/calibre.app/Contents/MacOS/` or linked to `/usr/local/bin` or `/opt/homebrew/bin`.
  - Verify installation by running `calibredb --version` in your terminal.

## Installation

1. **Clone or Copy the Repository**:
   Ensure you have the `calibre_mcp` directory and `requirements.txt`.

2. **Install Dependencies**:
   It is recommended to use a virtual environment.
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The server requires the path to your Calibre library if it is not in the default location.

- **Environment Variable**: `CALIBRE_LIBRARY_PATH`
  - Example: `/Users/username/Calibre Library`

## Usage

You can run the server directly for testing, but it is designed to be run by an MCP client.

### Running Manually (for testing)
```bash
# Optional: Set library path
export CALIBRE_LIBRARY_PATH="/path/to/your/library"

# Run the server
python3 server.py
```

### Running with Docker

1. **Build the image**:
   ```bash
   docker build -t calibre-mcp .
   ```

2. **Run the container**:
   You need to mount your Calibre library into the container.
   ```bash
   docker run -i --rm \
     -v "/path/to/your/library:/library" \
     -e CALIBRE_LIBRARY_PATH="/library" \
     calibre-mcp
   ```

   Or using Docker Compose:
   ```bash
   export CALIBRE_LIBRARY_PATH="/path/to/your/library"
   docker-compose up --build
   ```

    *Note: When using with an MCP client like Claude Desktop, you will need to configure the client to run the `docker run` command. See [Docker Setup Guide](docs/docker_setup.md) for detailed configuration instructions.*

### Running inside linuxserver/calibre-web

Instead of a separate container, you can run this MCP server **inside** an existing
`lscr.io/linuxserver/calibre-web` container using linuxserver's `custom-cont-init.d`
and `custom-services.d` hooks. The server runs as a supervised s6 service (SSE on
port 8084) with its own isolated virtualenv.

See the [calibre-web Integration Guide](docs/calibre_web_integration.md) for the full
compose snippet and troubleshooting.


## Client Configuration

### Claude Desktop

Add the following to your `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "calibre": {
      "command": "/path/to/python3",
      "args": [
        "/absolute/path/to/calibre_mcp/server.py"
      ],
      "env": {
        "CALIBRE_LIBRARY_PATH": "/absolute/path/to/Calibre Library"
      }
    }
  }
}
```
*Note: Replace `/path/to/python3` with your actual Python executable path (run `which python3` to find it).*

### Cursor

1. Go to **Cursor Settings** > **Features** > **MCP**.
2. Click **Add New MCP Server**.
3. **Name**: Calibre
4. **Type**: stdio
5. **Command**: `/path/to/python3` (e.g., `/usr/bin/python3` or from your venv)
6. **Arguments**: `/absolute/path/to/calibre_mcp/server.py`
7. **Environment Variables**:
   - Key: `CALIBRE_LIBRARY_PATH`
   - Value: `/absolute/path/to/Calibre Library`

## Tools Reference

| Tool | Description | Arguments | Returns |
|------|-------------|-----------|---------|
| `search_books` | Search for books in the library. | `query` (string): Search query (e.g., `title:Python`) | List of books (`id`, `title`, `authors`) |
| `get_book_details` | Get detailed metadata for a specific book. | `book_id` (int): Calibre book ID | Dictionary with full metadata |
| `add_book` | Add a new file to the library. | `file_path` (string): Absolute path to file | Success message with new Book ID |
| `convert_book` | Convert a book to a different format. | `book_id` (int), `output_format` (string) | Success message |
| `delete_book` | Delete a book from the library permanently. | `book_id` (int) | Status message |
| `export_book` | Export a book to a specific directory. | `book_id` (int), `output_dir` (string) | Status message |
| `update_book` | Update book metadata. | `book_id` (int), `title` (str, opt), `authors` (str, opt) | Status message |
| `manage_tags` | Add or remove tags from a book. | `book_id` (int), `add_tags` (list), `remove_tags` (list) | Status message |
| `set_cover` | Set the cover image for a book. | `book_id` (int), `cover_path` (string) | Status message |
| `get_cover_path` | Get the local path to the book's cover image. | `book_id` (int) | Absolute path to cover image |
| `read_book_content` | Read the text content of a book. | `book_id` (int) | Text content (truncated if large) |
| `list_categories` | List available categories. | `category_type` (string): e.g., `tags`, `authors` | List of category names |
| `check_library` | Run a consistency check on the library. | None | Check report |
| `get_library_stats` | Get statistics about the library. | None | Stats dictionary |

## Troubleshooting

- **`calibredb executable not found`**: Ensure the directory containing `calibredb` is in your system PATH, or that you are launching the MCP client with the correct environment variables.
- **`Book not found`**: Verify the Book ID using `search_books`.
- **Conversion Failures**: Ensure `ebook-convert` is installed. Some conversions (e.g., DRM-protected files) may fail.
