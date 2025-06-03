# Ocelonis Frontend

A modern React frontend for the Ocelonis application - a sophisticated web interface for uploading OCEL 2.0 files to Celonis. Built with React 19, TanStack Router, and Tailwind CSS, featuring real-time WebSocket communication, elegant UI components, and a sleek dark theme.

## Features

- **Modern React Architecture**: Built with React 19 and TanStack Router for optimal performance
- **Real-time Communication**: WebSocket integration for live updates and interactive workflows
- **Elegant UI/UX**: Dark theme with animated gradients, responsive design, and smooth transitions
- **File Upload Interface**: Drag-and-drop file upload with progress tracking
- **Authentication Flow**: Secure login with MFA support through modal interfaces
- **Live Logging**: Real-time log display with session-specific message filtering
- **Responsive Design**: Mobile-first approach with responsive breakpoints
- **Modern Styling**: Tailwind CSS with custom animations and shadcn/ui components
- **Type Safety**: Full TypeScript support with strict type checking

## Technology Stack

- **Framework**: React 19 with TypeScript
- **Routing**: TanStack Router with file-based routing
- **Styling**: Tailwind CSS 4 with custom animations
- **UI Components**: Radix UI primitives with shadcn/ui
- **State Management**: Zustand for global state
- **Build Tool**: Vite for fast development and optimized builds
- **Testing**: Vitest with React Testing Library
- **Icons**: Lucide React icons

## Installation

This project uses [pnpm](https://pnpm.io/) for package management.

1. Install dependencies:
```bash
pnpm install
```

2. Start the development server:
```bash
pnpm start  
```

The application will be available at `http://localhost:3000`

## Development Commands

```bash
# Start development server
pnpm dev
# or
pnpm start

# Build for production
pnpm build

# Preview production build
pnpm serve

# Run tests
pnpm test
```

## Project Structure

```
src/
├── components/           # React components
│   ├── ui/              # Reusable UI components (shadcn/ui)
│   ├── header.tsx       # Main header with animated logo
│   ├── control-panel.tsx # Main control interface
│   ├── logs-panel.tsx   # Real-time log display
│   ├── login-modal.tsx  # Authentication modal
│   └── mfa-modal.tsx    # MFA verification modal
├── routes/              # TanStack Router routes
│   ├── __root.tsx       # Root layout component
│   └── index.tsx        # Main application page
├── lib/                 # Utility libraries and configurations
├── styles.css           # Global styles and Tailwind configuration
└── main.tsx            # Application entry point
```

## Component Architecture

### Header Component
- **Logo Integration**: Displays both Ocelonis and HapLab logos
- **Animated Gradient**: Smooth flowing gradient animation on the title
- **Responsive Design**: Adapts to different screen sizes

### Control Panel
- **File Upload**: Drag-and-drop interface with visual feedback
- **Authentication**: Integrated login flow with MFA support
- **Process Management**: Step-by-step workflow controls
- **Real-time Updates**: Live status updates via WebSocket

### Logs Panel
- **Live Streaming**: Real-time log display with WebSocket integration
- **Session Filtering**: Shows only logs relevant to the current session
- **Auto-scroll**: Automatically scrolls to show latest messages
- **Styled Output**: Formatted log messages with appropriate styling

### Modal System
- **Login Modal**: Secure credential input with validation
- **MFA Modal**: Multi-factor authentication code input
- **Accessible**: Full keyboard navigation and screen reader support
- **Responsive**: Works seamlessly across all device sizes

## Styling and Theming

The application uses a sophisticated dark theme with:

- **Color Palette**: Black background with gray text and emerald/cyan/purple accents
- **Typography**: Modern font stack with monospace elements for technical content
- **Animations**: Smooth transitions and gradient animations using CSS keyframes
- **Responsive Design**: Mobile-first approach with Tailwind's responsive utilities
- **Custom Components**: shadcn/ui components customized for the dark theme

## WebSocket Integration

The frontend connects to the backend WebSocket API for:

- **Real-time Logging**: Session-specific log messages
- **Authentication Flow**: Interactive login and MFA processes
- **File Processing**: Live updates during OCEL file processing
- **Session Management**: Automatic session handling and cleanup

### WebSocket Events

```typescript
// Connection established
{ type: "connected", session_id: "uuid", message: "..." }

// Log messages
{ type: "log_message", level: "info|warning", message: "..." }

// Command responses
{ type: "login_success|mfa_required|error", message: "..." }
```

## Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```bash
# API Endpoints (optional - defaults to localhost)
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

### Vite Configuration

The project uses Vite with:
- React plugin for Fast Refresh
- TypeScript support
- Path aliases (`@/` for `src/`)
- Tailwind CSS integration

## Building for Production

```bash
# Build the application
pnpm build

# Preview the build
pnpm serve
```

The build output will be in the `dist/` directory, ready for deployment to any static hosting service.

## Testing

The project uses Vitest with React Testing Library for comprehensive testing:

```bash
# Run all tests
pnpm test

# Run tests in watch mode
pnpm test --watch

# Run tests with coverage
pnpm test --coverage
```

## Browser Support

- **Modern Browsers**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile**: iOS Safari 14+, Chrome Mobile 90+
- **Features**: ES2020, CSS Grid, Flexbox, WebSockets, File API

## Contributing

1. Follow the existing code style and component patterns
2. Use TypeScript for all new code
3. Maintain responsive design principles
4. Test components thoroughly
5. Update documentation for new features

## Architecture Decisions

- **File-based Routing**: TanStack Router for automatic route generation
- **Component Composition**: Radix UI primitives for accessibility
- **State Management**: Zustand for lightweight global state
- **Styling**: Tailwind CSS for utility-first styling
- **Type Safety**: Strict TypeScript configuration

## Performance Considerations

- **Code Splitting**: Automatic route-based code splitting
- **Lazy Loading**: Dynamic imports for non-critical components
- **Optimized Images**: Proper image sizing and formats
- **Bundle Analysis**: Vite's built-in bundle analysis tools

## Credits

- **Created in collaboration with**: [HapLab](https://www.haplab.org/)
- **UI Components**: [shadcn/ui](https://ui.shadcn.com/)
- **Icons**: [Lucide React](https://lucide.dev/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
