# Photoroom Tools Configuration
# Add your tools here and they will automatically appear in the navigation

TOOLS_CONFIG = {
    "brand": {
        "name": "Photoroom UA Video Tools",
        "icon": "fas fa-photo-video",
        "url": "#"
    },
    "tools": [
        {
            "name": "Video Converter",
            "icon": "fas fa-tools",
            "url": "#",
            "active": True,
            "description": "Convert videos to different formats (square, landscape, vertical)"
        },
        {
            "name": "AdLocalizer",
            "icon": "fas fa-language",
            "url": "https://photoroomadlocalizer.onrender.com/",
            "active": True,
            "description": "AI-powered video localization and translation"
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