# AIMailer Admin Dashboard

Modern React-based admin dashboard for managing AIMailer email automation system.

## 🎨 Features

- **Dashboard**: Real-time metrics and performance insights
- **Pending Reviews**: Review and approve low-confidence email responses
- **Recent Emails**: View processing history and status
- **Analytics**: Comprehensive charts and data visualization
- **Export**: Generate analytics reports

## 🚀 Quick Start

### Prerequisites
- Node.js 16+ installed
- API server running (`python api_server.py`)

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

Dashboard will be available at: **http://localhost:3000**

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## 🔌 API Configuration

The dashboard connects to the Flask API server at `http://localhost:5000`

To change the API URL, edit `vite.config.js`:

```javascript
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://your-api-server:5000',
        changeOrigin: true,
      }
    }
  }
})
```

Or set environment variable:

```bash
VITE_API_URL=http://your-api-server:5000/api
```

## 📁 Project Structure

```
admin-dashboard/
├── src/
│   ├── main.jsx              # App entry point
│   ├── App.jsx               # Main app component with routing
│   ├── components/
│   │   └── Navigation.jsx    # Top navigation bar
│   ├── pages/
│   │   ├── Dashboard.jsx     # Dashboard page
│   │   ├── PendingReviews.jsx # Review emails page
│   │   ├── RecentEmails.jsx  # Email history page
│   │   └── Analytics.jsx     # Analytics page
│   └── services/
│       └── api.js            # API client service
├── public/                   # Static assets
├── index.html                # HTML template
├── package.json              # Dependencies
└── vite.config.js           # Vite configuration
```

## 🎯 Key Components

### Dashboard Page
- Total emails processed
- Auto-replied count
- Pending reviews count
- Failed emails count
- Performance metrics
- System recommendations

### Pending Reviews Page
- List of emails requiring manual review
- View email details and FAQ matches
- Edit AI-generated responses
- Generate custom responses
- Approve and send emails
- Admin email tracking

### Recent Emails Page
- Complete email processing history
- Status indicators (success, pending, failed)
- Confidence scores
- Processing times
- Response sent status

### Analytics Page
- Period selection (daily, weekly, monthly)
- Summary statistics
- Performance metrics charts
- Automation rate tracking
- Export functionality

## 🎨 Customization

### Theme Colors

Edit `src/main.jsx`:

```javascript
const theme = createTheme({
  palette: {
    primary: {
      main: '#4CAF50', // Change primary color
    },
    secondary: {
      main: '#2196F3', // Change secondary color
    },
  },
});
```

### Add New Pages

1. Create component in `src/pages/`
2. Add route in `src/App.jsx`
3. Add navigation item in `src/components/Navigation.jsx`

## 🔧 Dependencies

### Core
- **React 18**: UI framework
- **React Router 6**: Routing
- **Material-UI 5**: Component library
- **Axios**: HTTP client

### Visualization
- **Recharts**: Charts and graphs

### Utilities
- **date-fns**: Date formatting
- **react-toastify**: Notifications

## 📱 Responsive Design

The dashboard is fully responsive and works on:
- Desktop (1920px+)
- Laptop (1366px+)
- Tablet (768px+)
- Mobile (320px+)

## 🔒 Authentication

Currently, the dashboard requires admin email input when approving responses. This is stored in browser localStorage for convenience.

To add full authentication:
1. Implement login system in API server
2. Add JWT token handling
3. Create login page component
4. Add protected routes

## 🐛 Troubleshooting

### Dashboard shows "Failed to load data"
- Ensure API server is running on port 5000
- Check browser console for CORS errors
- Verify `vite.config.js` proxy settings

### Charts not rendering
- Check if Recharts is installed: `npm list recharts`
- Clear browser cache
- Try different browser

### Slow performance
- Build production version: `npm run build`
- Reduce data fetch intervals
- Implement pagination for large datasets

## 📊 Performance Tips

1. **Use Production Build** for deployment
2. **Enable Gzip** compression on server
3. **Implement caching** for static assets
4. **Lazy load** components for faster initial load

## 🚀 Deployment

### Netlify/Vercel

```bash
npm run build
# Deploy 'dist' folder
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

## 📈 Future Enhancements

- [ ] Real-time WebSocket updates
- [ ] Advanced filtering and search
- [ ] Bulk operations
- [ ] User management
- [ ] Role-based access control
- [ ] Dark mode toggle
- [ ] Email template editor
- [ ] FAQ database manager
- [ ] System health monitoring
- [ ] Notification system

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📝 License

Same as parent AIMailer project

---

**Built with ❤️ using React + Material-UI + Vite**
