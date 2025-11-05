# KePrompt Web GUI

Modern, single-page application (SPA) interface for KePrompt.

## Overview

This web interface provides a clean, intuitive way to interact with KePrompt through your browser. It's organized into tabs for each major feature of KePrompt.

## Features

### 💬 Chats Tab
- **Two-panel layout**: Chat list on the left, conversation interface on the right
- **Real-time messaging**: Send messages and receive AI responses
- **Chat management**: Create new chats, delete existing ones
- **Modern chat UI**: Similar to popular AI chat interfaces (ChatGPT, Claude, etc.)
- **Message history**: View full conversation history with timestamps

### 📝 Prompts Tab
- View all available prompt files
- See prompt descriptions and metadata
- Search and filter prompts

### 🤖 Models Tab
- Browse all available AI models
- Filter by provider, company, or name
- View model specifications (max tokens, pricing, features)
- See support for vision and function calling

### 🔌 Providers Tab
- View all API providers
- See model counts per provider
- See which companies are available through each provider

### ⚙️ Functions Tab
- View all available custom functions
- See function parameters and descriptions
- Identify required vs optional parameters

### 💾 Database Tab
- View database statistics (size, chat count)
- Monitor database health

### 🖥️ Server Tab
- View server status and version
- Health monitoring

## Technology Stack

- **Pure HTML/CSS/JavaScript** - No build tools required
- **Modern CSS** - CSS Grid, Flexbox, CSS Variables
- **Fetch API** - RESTful API communication
- **Responsive Design** - Works on desktop and mobile

## Starting the Web GUI

From your keprompt project directory:

```bash
keprompt server start --web-gui
```

By default, the server runs on `http://localhost:8080`

You can also specify a custom port:

```bash
keprompt server start --web-gui --port 3000
```

## Usage

1. **Start the server** with `--web-gui` flag
2. **Open your browser** to `http://localhost:8080` (or your custom port)
3. **Create a chat** by clicking "+ New Chat" and selecting a prompt
4. **Send messages** and interact with the AI
5. **Browse other tabs** to explore models, prompts, functions, etc.

## File Structure

```
web-gui/
├── index.html      # Main HTML structure with tabs and modals
├── styles.css      # Modern styling with CSS variables
├── app.js          # JavaScript application logic and API client
└── README.md       # This file
```

## API Integration

The web GUI communicates with the KePrompt REST API at `/api/*` endpoints:

- `/api/chats` - Chat management
- `/api/prompts` - Prompt discovery
- `/api/models` - Model information
- `/api/providers` - Provider listing
- `/api/functions` - Function catalog
- `/api/database` - Database statistics
- `/health` - Server health check

## Design Features

### Color Scheme
- **Primary**: Blue (`#2563eb`)
- **Success**: Green (`#16a34a`)
- **Danger**: Red (`#dc2626`)
- **Background**: Light gray (`#f8fafc`)
- **Surface**: White (`#ffffff`)

### UI Components
- **Cards** - For displaying grouped information
- **Tables** - For structured data (models, etc.)
- **Modals** - For create/confirm actions
- **Badges** - For status indicators
- **Loading states** - Animated loading indicators
- **Error messages** - Clear error display

### Responsive Design
- Desktop-first with mobile adaptations
- Collapsible chat list on small screens
- Flexible grid layouts
- Touch-friendly buttons and inputs

## Browser Support

Modern browsers with ES6+ support:
- Chrome 60+
- Firefox 60+
- Safari 12+
- Edge 79+

## Development

To modify the interface:

1. Edit the HTML structure in `index.html`
2. Update styles in `styles.css`
3. Modify behavior in `app.js`
4. Refresh your browser to see changes (use `--reload` flag for auto-reload during development)

For development with auto-reload:

```bash
keprompt server start --web-gui --reload
```

## Notes

- The web GUI requires the KePrompt HTTP server to be running
- All data is fetched from the REST API in real-time
- No data is stored in the browser (except session state)
- The interface automatically checks API connectivity on load
