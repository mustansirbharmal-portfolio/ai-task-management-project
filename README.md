# Smart Task Analyzer

An intelligent task management system that scores and prioritizes tasks based on multiple factors using AI-powered analysis.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Django](https://img.shields.io/badge/Django-4.2-green.svg)
![Azure](https://img.shields.io/badge/Azure-OpenAI%20%7C%20CosmosDB-blue.svg)

## 🚀 Features

- **Intelligent Priority Scoring**: Multi-factor algorithm considering urgency, importance, effort, and dependencies
- **Multiple Sorting Strategies**: Smart Balance, Fastest Wins, High Impact, Deadline Driven
- **Eisenhower Matrix**: Visual 2D grid categorizing tasks by urgency and importance
- **Date Intelligence**: AI-powered weekend/holiday consideration for corporate tasks
- **Learning System**: Feedback-driven weight optimization using Azure OpenAI
- **Circular Dependency Detection**: Automatic detection and flagging of dependency cycles
- **Responsive UI**: Professional black & white themed interface

## 📋 Table of Contents

- [Setup Instructions](#setup-instructions)
- [Algorithm Explanation](#algorithm-explanation)
- [API Endpoints](#api-endpoints)
- [Design Decisions](#design-decisions)
- [Running Tests](#running-tests)
- [Future Improvements](#future-improvements)

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.9 or higher
- Azure Cosmos DB account
- Azure OpenAI service (GPT-4o deployment)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "AI Powered Task Generator"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create or update `.env` file with your Azure credentials:
   ```env
   # Azure Cosmos DB
   COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com/
   COSMOS_KEY=your-cosmos-key
   COSMOS_DATABASE_NAME=task-management
   COSMOS_CONTAINER_NAME=data
   
   # Azure OpenAI
   AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
   AZURE_OPENAI_API_KEY=your-openai-key
   AZURE_OPENAI_API_VERSION=2023-05-15
   AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
   
   # Django
   SECRET_KEY=your-secret-key
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Start the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   
   Open your browser and navigate to `http://localhost:8000`

## 🧮 Algorithm Explanation

### Priority Scoring System (300-500 words)

The Smart Task Analyzer employs a sophisticated multi-factor scoring algorithm that transforms task attributes into a unified priority score. The system normalizes all factors to a 0-1 scale before combining them using configurable weights.

#### Factor Calculations

**1. Urgency Score (0-1+)**
- Calculated based on days until due date
- Overdue tasks receive scores > 1.0 (with an overdue bonus of up to 0.3)
- Due today = 1.0, linear decay over 30 days
- For corporate tasks, weekends are excluded from the calculation using AI classification

**2. Importance Score (0-1)**
- Direct normalization of user's 1-10 rating
- Formula: `importance / 10`

**3. Effort/Easiness Score (0-1)**
- Inverse logarithmic relationship with estimated hours
- Lower effort = higher score (quick wins prioritization)
- Formula: `1 - (log(hours + 1) / log(MAX_HOURS + 1))`

**4. Blocking Score (0-1)**
- Measures how many other tasks depend on this task
- Uses square root for diminishing returns
- Formula: `sqrt(blocked_count / (total_tasks - 1))`

#### Weighted Combination

The final score uses a weighted sum:
```
score = w1*urgency + w2*importance + w3*effort + w4*blocking
```

Default weights (Smart Balance): 30% urgency, 30% importance, 20% effort, 20% blocking

#### Strategy Presets

| Strategy | Urgency | Importance | Effort | Blocking |
|----------|---------|------------|--------|----------|
| Smart Balance | 30% | 30% | 20% | 20% |
| Fastest Wins | 15% | 15% | 60% | 10% |
| High Impact | 15% | 60% | 10% | 15% |
| Deadline Driven | 60% | 20% | 10% | 10% |

#### Dependency Handling

The algorithm uses topological sorting to ensure tasks are never suggested before their dependencies. Circular dependencies are detected using DFS and flagged to users.

#### Learning System

User feedback (helpful/not helpful) is collected and used to adjust weights:
1. Heuristic adjustment: Increases weights for factors that were high in helpful suggestions
2. AI-powered optimization: Uses GPT-4o to analyze patterns and suggest optimal weights

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/tasks/analyze/` | Analyze and score a list of tasks |
| GET | `/api/tasks/suggest/` | Get top 3 task suggestions |
| GET/POST | `/api/tasks/matrix/` | Get Eisenhower Matrix categorization |
| GET/POST | `/api/tasks/weights/` | Manage user weight configuration |
| POST | `/api/tasks/feedback/` | Submit feedback on suggestions |
| POST | `/api/tasks/learn/` | Trigger AI weight optimization |
| GET | `/api/tasks/` | Get all stored tasks |

### Example Request

```bash
curl -X POST http://localhost:8000/api/tasks/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {
        "title": "Fix login bug",
        "due_date": "2025-11-30",
        "estimated_hours": 3,
        "importance": 8,
        "dependencies": []
      }
    ],
    "strategy": "smart_balance"
  }'
```

## 🎨 Design Decisions

### Trade-offs Made

1. **Weighted Sum vs Multiplication**
   - Chose weighted sum for interpretability and configurability
   - Multiplication would require all factors to be high, which is too restrictive

2. **Logarithmic Effort Scaling**
   - Linear scaling would over-penalize long tasks
   - Log scale provides better distribution across typical task durations

3. **Cosmos DB for Storage**
   - Chose Cosmos DB for scalability and Azure ecosystem integration
   - Trade-off: Higher cost than SQLite for small deployments

4. **AI Classification for Date Intelligence**
   - Real-time API calls add latency
   - Trade-off: Better accuracy for corporate vs personal task handling

5. **Client-side Task Storage**
   - Tasks are stored both locally and in Cosmos DB
   - Trade-off: Enables offline-first experience but requires sync logic

### Why These Choices?

- **Pydantic for Validation**: Type safety and automatic error messages
- **Bootstrap for UI**: Rapid development with responsive design
- **Black/White Theme**: Professional appearance, reduces visual noise

## 🧪 Running Tests

```bash
# Run all tests
pytest tasks/tests.py -v

# Run specific test class
pytest tasks/tests.py::TestUrgencyScoring -v

# Run with coverage
pytest tasks/tests.py --cov=tasks
```

### Test Coverage

- **Scoring Correctness**: Urgency, importance, effort, blocking calculations
- **Overdue Handling**: Past-due tasks receive appropriate priority boost
- **Dependency Logic**: Topological sorting and cycle detection
- **Edge Cases**: Missing fields, invalid input, empty lists, extreme values

### 🔥 Tough Edge Case Tests

5 rigorous edge case tests designed to stress-test the algorithm:

```bash
# Run tough edge case tests
pytest tasks/tests.py::TestToughEdgeCases -v
```

#### Test Results: ✅ 5/5 PASSED

---

#### Edge Case 1: Large Scale Linear Dependency Chain

**Scenario**: 100 tasks in a linear dependency chain (Task-0 → Task-1 → Task-2 → ... → Task-99)

| Metric | Value |
|--------|-------|
| **Approach** | Creates a long chain where each task depends on the previous one |
| **Time Complexity** | O(n²) - For each task, checks all others for dependencies |
| **Space Complexity** | O(n) - Storing n tasks and analyzed results |
| **Efficiency** | Tests topological sorting and blocking score at scale |

**What it Tests**:
- Deep recursion handling in dependency graphs
- Blocking score calculation (Task-0 blocks 99 tasks)
- No false cycle detection in valid linear chains

---

#### Edge Case 2: Complex Diamond + Cross Dependency Graph

**Scenario**: 8 tasks with diamond patterns and cross-dependencies

```
            [A]
           / | \
         [B][C][D]
          \ | /|
           [E] |
           / \ |
         [F] [G]
          \ /
           [H]
```

| Metric | Value |
|--------|-------|
| **Approach** | Tests multiple convergent and divergent paths |
| **Time Complexity** | O(V + E) - DFS cycle detection |
| **Space Complexity** | O(V) - Visited set and recursion stack |
| **Efficiency** | Tests complex graph topologies without false positives |

**What it Tests**:
- Multiple convergent/divergent dependency paths
- Correct Eisenhower matrix distribution
- No false cycle detection in complex valid graphs

---

#### Edge Case 3: All Tasks Overdue (20 Tasks)

**Scenario**: 20 tasks overdue by 2-40 days with varying importance (1-10)

| Metric | Value |
|--------|-------|
| **Approach** | Tests urgency boost calculation for overdue tasks |
| **Time Complexity** | O(n log n) - Sorting by priority |
| **Space Complexity** | O(n) - Storing analyzed tasks |
| **Efficiency** | Tests overdue penalty scaling and priority differentiation |

**What it Tests**:
- All tasks marked as overdue with urgency > 1.0
- Correct priority ordering balancing overdue severity with importance
- Priority scores in descending order

---

#### Edge Case 4: Extreme Boundary Values

**Scenario**: 7 tasks with extreme/boundary values

| Task | Hours | Importance | Due Date |
|------|-------|------------|----------|
| Tiny Task | 0.01h (36 sec) | 5 | Today |
| Massive Project | 10,000h | 10 | +1 year |
| Zero Priority | 2h | 0 (invalid) | +7 days |
| Critical Override | 1h | 100 (invalid) | Today |
| Forgotten Task | 5h | 8 | -10 years |
| Long Term Goal | 100h | 3 | +10 years |
| Invalid Hours | -5h (invalid) | 5 | Today |

| Metric | Value |
|--------|-------|
| **Approach** | Tests input validation, clamping, numerical stability |
| **Time Complexity** | O(n) - Processing each task |
| **Space Complexity** | O(1) per task scoring |
| **Efficiency** | Tests graceful degradation with invalid inputs |

**What it Tests**:
- Importance clamping (0→1, 100→10)
- Effort score boundaries (0.01h → >0.9, 10000h → ≤0.1)
- Urgency handling for extreme dates (10 years ago/future)
- Graceful handling of negative hours

---

#### Edge Case 5: Multiple Overlapping Circular Dependencies

**Scenario**: 10 nodes with 3 overlapping cycles + 1 isolated node

```
    [A] ←→ [B]     (Cycle 1: A-B)
     ↓      ↓
    [C] → [D] → [E]
     ↑           ↓
     └─────[F]←──┘  (Cycle 2: C-D-E-F-C)
     
    [G] → [H] → [I] → [G]  (Cycle 3: G-H-I-G, isolated)
    
    [J]  (Non-cyclic, isolated)
```

| Metric | Value |
|--------|-------|
| **Approach** | Tests detection of multiple independent and overlapping cycles |
| **Time Complexity** | O(V + E) - DFS with coloring |
| **Space Complexity** | O(V) - Visited states |
| **Efficiency** | Tests robustness of cycle detection algorithm |

**What it Tests**:
- Detection of multiple independent cycles
- Overlapping cycle detection
- Isolated non-cyclic nodes excluded from cycle list

---

### Overall Algorithm Complexity

| Operation | Time Complexity | Space Complexity |
|-----------|-----------------|------------------|
| Task Scoring | O(n) | O(1) |
| Blocking Score | O(n²) | O(n) |
| Cycle Detection | O(V + E) | O(V) |
| Priority Sorting | O(n log n) | O(n) |
| Eisenhower Matrix | O(n) | O(n) |
| **Full Analysis** | **O(n²)** | **O(n)** |

## 🎯 Bonus Challenges Attempted

- ✅ **Date Intelligence**: Azure OpenAI integration for corporate task detection
- ✅ **Eisenhower Matrix UI**: Visual 2D grid categorization
- ✅ **Learning System**: Feedback collection and AI-powered weight optimization
- ✅ **Configurable Weights**: User-adjustable scoring parameters
- ✅ **Circular Dependency Detection**: DFS-based cycle detection

## 🔮 Future Improvements

With more time, I would implement:

1. **User Authentication**: Multi-user support with personalized weights
2. **Task Completion Tracking**: Mark tasks as done, track productivity
3. **Calendar Integration**: Sync with Google Calendar, Outlook
4. **Recurring Tasks**: Support for repeating tasks
5. **Team Collaboration**: Shared task lists, delegation features
6. **Mobile App**: React Native or Flutter implementation
7. **Notifications**: Email/push reminders for upcoming deadlines
8. **Analytics Dashboard**: Productivity metrics, completion trends
9. **Natural Language Input**: "Add task: fix bug by Friday" parsing
10. **Offline Support**: Service worker for offline functionality

## 📄 License

MIT License - feel free to use this project for learning and development.

---

Built with ❤️ using Django, Azure OpenAI, and Azure Cosmos DB
