# Cookie Clicker Calculator - Web Version

## 🚀 Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🎮 Running the Application

Start the web server:
```bash
python app.py
```

Then open your browser at: **http://localhost:5000**

## ✨ Features

### Interactive Mode
- 🎯 View all upgrades in a beautiful table with best upgrade highlighted
- 📊 Real-time CPS tracking and statistics
- 🛒 Purchase upgrades with one click
- 📈 Interactive Plotly charts showing CPS distribution
- 💾 Export data to CSV/JSON
- ✅ Visual notifications for all actions

### Automatic Simulation
- 🚀 Simulate up to 10,000 purchases instantly
- 📊 Real-time progress bar with percentage
- 📉 4 interactive charts:
  - CPS Distribution bar chart
  - Purchases vs Time Investment dual-axis
  - CPS Growth Timeline with milestones
  - Cost vs CPS Heatmap (bubble chart)
- 💾 Export simulation results
- 📜 Simulation history with timestamps
- ⚡ Input validation (1-10,000 purchases)

### User Experience Improvements
- 🎨 Modern gradient UI design (purple/pink theme)
- 🔔 Toast notifications for success/error messages
- ⚡ Debounced chart refreshes for smooth performance
- 🛡️ Comprehensive error handling throughout
- ✅ Form validation with helpful error messages
- 🎯 Responsive design for all screen sizes

### Performance Optimizations
- **LRU Cache**: `calculate_time_to_reach_cost` cached for 10x+ speed boost
- **Debouncing**: Chart refreshes debounced to prevent excessive redraws
- **Efficient computation**: Avoiding redundant calculations
- **Timeline sampling**: Tracking every 10 purchases (not every single one)
- **Input validation**: Server-side and client-side validation

### Data Management
- 💾 Export current upgrades to CSV/JSON
- 📥 Download simulation results with timestamp
- 📂 Access complete simulation history
- 🔄 Auto-save all simulations to disk

### Security & Robustness
- 🛡️ Server-side validation on all API endpoints
- ⚠️ Comprehensive error handling with meaningful messages
- 📝 Request validation (type checking, range validation)
- 🚫 Protection against invalid inputs

## 📁 File Structure

```
cc-calc/
├── app.py                           # Flask backend with error handling
├── templates/
│   └── index.html                   # Frontend UI with notifications
├── cookie_clicker_upgrades.json     # Upgrade data (persistent)
├── simulations/                     # Auto-created for results
│   ├── simulation_TIMESTAMP.json
│   └── simulation_TIMESTAMP.csv
├── requirements.txt                 # Python dependencies
├── .gitignore                       # Git ignore file
└── README_WEB.md                    # This file
```

## 🎨 Technologies Used

- **Backend**: Flask (Python) with comprehensive error handling
- **Frontend**: HTML5, CSS3 (gradients, animations), Vanilla JavaScript
- **Charts**: Plotly.js (interactive visualizations)
- **Data**: Pandas (CSV export), JSON (persistence)
- **Caching**: functools.lru_cache (performance optimization)
- **Validation**: Server-side and client-side input validation

## 🔧 API Endpoints

All endpoints include error handling and return meaningful error messages.

- `GET /` - Main application
- `GET /api/upgrades` - Get all upgrades with metrics
- `POST /api/upgrade/<name>` - Purchase an upgrade (with validation)
- `POST /api/simulate` - Run simulation (validates 1-10,000 purchases)
- `GET /api/charts/<type>` - Get chart data
- `POST /api/simulation-charts` - Get simulation charts (with error handling)
- `GET /api/export/<format>` - Export data (csv/json)
- `GET /api/simulations` - List all simulations

## 💡 Tips

- ✅ Use Interactive Mode to track your real game progress
- 🎯 Use Simulation Mode to plan ahead and test strategies
- 🖱️ Charts are interactive - click, zoom, and hover for details
- 💾 All simulations are automatically saved with timestamps
- 🔔 Watch for toast notifications in the bottom-right corner
- ⚡ Simulations are limited to 10,000 purchases for performance
- 📊 Export data anytime to analyze in Excel or other tools

## 🐛 Error Handling

The application includes comprehensive error handling:
- ✅ Input validation on both client and server
- 🔔 Visual feedback for all operations
- 📝 Meaningful error messages
- 🛡️ Protection against invalid data
- ⚠️ Graceful degradation on failures

Enjoy optimizing your cookie production! 🍪✨

