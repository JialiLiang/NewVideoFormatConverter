# Photoroom Tools Configuration
# Add your tools here and they will automatically appear in the navigation

TOOLS_CONFIG = {
    "brand": {
        "name": "Photoroom UA Video Tools",
        "icon": "fas fa-photo-video",
        "url": "/"
    },
    "tools": [
        {
            "name": "Video Converter",
            "icon": "fas fa-tools",
            "url": "/video-converter",
            "active": True,
            "description": "Convert videos to different formats (square, landscape, vertical)"
        },
        {
            "name": "AdLocalizer",
            "icon": "fas fa-language",
            "url": "/adlocalizer",
            "active": True,
            "description": "AI-powered video localization and translation"
        },
        {
            "name": "Creative Name Generator",
            "icon": "fas fa-magic",
            "url": "/name-generator",
            "active": True,
            "description": "Generate creative file names following naming conventions"
        },
        {
            "name": "YouTube Playlist Extractor",
            "icon": "fab fa-youtube",
            "url": "/youtube-playlist",
            "active": True,
            "description": "Extract video IDs from YouTube playlists (public, unlisted, private)"
        },
        {
            "name": "YouTube Playlist Batch Creator",
            "icon": "fab fa-youtube",
            "url": "/youtube-playlist-batch",
            "active": True,
            "description": "Create standardized unlisted playlists in bulk"
        },
        {
            "name": "YouTube Bulk Uploader",
            "icon": "fab fa-youtube",
            "url": "/youtube-uploader",
            "active": True,
            "description": "Upload videos and attach them to playlists in bulk"
        },
        {
            "name": "Static Generator (WIP)",
            "icon": "fas fa-file-code",
            "url": "/static-generator",
            "active": True,
            "description": "Generate static content and assets"
        },
        {
            "name": "Hook Remixer (WIP)",
            "icon": "fas fa-music",
            "url": "/hook-remixer",
            "active": True,
            "description": "AI-powered music hook generation and remixing"
        },
        {
            "name": "Montage Maker (WIP)",
            "icon": "fas fa-film",
            "url": "/montage-maker",
            "active": True,
            "description": "Automated video montage creation"
        },
      
        # Add more tools here as you create them
        # {
        #     "name": "Video Editor",
        #     "icon": "fas fa-edit",
        #     "url": "https://your-video-editor-url.com/",
        #     "active": True,
        #     "description": "Edit and enhance your videos"
        # },
        # {
        #     "name": "Thumbnail Generator",
        #     "icon": "fas fa-image",
        #     "url": "https://your-thumbnail-generator-url.com/",
        #     "active": True,
        #     "description": "Generate eye-catching thumbnails"
        # }
    ]
}

def get_active_tools():
    """Get only active tools for navigation"""
    return [tool for tool in TOOLS_CONFIG["tools"] if tool.get("active", False)]

def get_tool_by_name(name):
    """Get a specific tool by name"""
    for tool in TOOLS_CONFIG["tools"]:
        if tool["name"].lower() == name.lower():
            return tool
    return None 
