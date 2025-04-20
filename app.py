# ultimate_speed_challenge.py
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from datetime import datetime
import os
import random

app = Flask(__name__)

# Game settings
GAME_DURATION = 30  # seconds
INITIAL_TARGET_DELAY = 0.8  # starts faster
MIN_TARGET_DELAY = 0.03  # 30ms (EXTREME SPEED)
DIFFICULTY_INCREASE_RATE = 0.65  # gets faster more aggressively
MAX_TARGETS = 4  # More targets simultaneously
TARGET_SIZE_REDUCTION = 2.0  # Targets shrink faster

# Data storage
DATA_DIR = 'game_data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

PLAYERS_FILE = os.path.join(DATA_DIR, 'players.dat')
WINNERS_FILE = os.path.join(DATA_DIR, 'winners.dat')

# Initialize files
for file_path in [PLAYERS_FILE, WINNERS_FILE]:
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            f.write("")

def save_player_data(name, phone, age, score, avg_reaction):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(PLAYERS_FILE, 'a') as f:
            f.write(f"{name}|{phone}|{age}|{score}|{avg_reaction:.1f}|{timestamp}\n")
        check_for_winner()
    except Exception as e:
        print(f"Error saving player data: {str(e)}")

def check_for_winner():
    try:
        with open(PLAYERS_FILE, 'r') as f:
            players = [line.strip().split('|') for line in f.readlines() if line.strip()]
    except Exception:
        return

    # Process players in groups of 5
    for i in range(0, len(players), 5):
        group = players[i:i+5]
        if len(group) == 5:
            # Sort by score (descending) and reaction time (ascending)
            group_sorted = sorted(group, key=lambda x: (-int(x[3]), float(x[4])))
            winner = group_sorted[0]
            
            try:
                with open(WINNERS_FILE, 'a') as f:
                    f.write(f"Winner: {winner[0]}|Phone: {winner[1]}|Age: {winner[2]}|Score: {winner[3]}|Reaction: {winner[4]}ms\n")
                    for p in group_sorted[1:]:
                        f.write(f"Player: {p[0]}|Phone: {p[1]}|Age: {p[2]}|Score: {p[3]}|Reaction: {p[4]}ms\n")
                    f.write("-----\n")
            except Exception as e:
                print(f"Error saving winner data: {str(e)}")

def get_player_position():
    try:
        with open(PLAYERS_FILE, 'r') as f:
            total_players = sum(1 for _ in f)
            position = total_players % 5 + 1
            return position, 5 - position  # Current position and players remaining
    except Exception:
        return 1, 4

def get_previous_scores():
    try:
        with open(PLAYERS_FILE, 'r') as f:
            players = [line.strip().split('|') for line in f.readlines() if line.strip()]
            group_start = (len(players) // 5) * 5
            return players[group_start:len(players)-1]
    except Exception:
        return []

# HTML Templates
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🔥 Ultimate Speed Challenge 🔥</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #3498db; --danger: #e74c3c; --success: #2ecc71;
            --warning: #f39c12; --dark: #111; --light: #222;
        }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: var(--dark);
            color: white;
        }
        .form-container {
            background-color: var(--light);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input, select {
            width: 100%;
            padding: 12px;
            background: #333;
            border: 1px solid #444;
            color: white;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            background: var(--warning);
            color: #000;
            border: none;
            padding: 14px;
            width: 100%;
            border-radius: 5px;
            font-weight: bold;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 10px;
        }
        button:hover {
            background: #ffc107;
            transform: translateY(-2px);
        }
        .position-info {
            background-color: var(--primary);
            padding: 10px;
            border-radius: 5px;
            margin-top: 20px;
            text-align: center;
            font-weight: bold;
        }
        .leaderboard-btn {
            background: #9b59b6;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <h1 style="text-align: center; color: var(--warning); margin-bottom: 30px;">🔥 Ultimate Speed Challenge 🔥</h1>
    <div class="form-container">
        <form action="/start" method="post">
            <div class="form-group">
                <label>Full Name:</label>
                <input type="text" name="name" required>
            </div>
            <div class="form-group">
                <label>Phone Number:</label>
                <input type="tel" name="phone" required>
            </div>
            <div class="form-group">
                <label>Age:</label>
                <input type="number" name="age" min="18" required>
            </div>
            <button type="submit">Start Challenge</button>
        </form>
        
        <button onclick="location.href='/leaderboard'" class="leaderboard-btn">
            🏆 View Leaderboard
        </button>
        
        {% if position %}
        <div class="position-info">
            You will be player {{ position }} in this group. 
            {% if remaining > 0 %}
                Waiting for {{ remaining }} more player{{ 's' if remaining > 1 }} to complete the group.
            {% else %}
                Group is complete! Your game will start now.
            {% endif %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

GAME_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🔥 Ultimate Speed Challenge 🔥</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        body {
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', system-ui, sans-serif;
            background-color: #111;
            color: white;
            touch-action: manipulation;
            overflow: hidden;
            -webkit-tap-highlight-color: transparent;
        }
        .game-container {
            position: relative;
            width: 100vw;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .game-header {
            display: flex;
            justify-content: space-between;
            padding: 12px 15px;
            background-color: #222;
            z-index: 10;
            box-shadow: 0 2px 10px rgba(0,0,0,0.5);
        }
        .game-stat {
            font-size: 16px;
            font-weight: bold;
            color: #ddd;
        }
        .game-stat span {
            color: white;
            font-size: 18px;
        }
        #game-area {
            flex: 1;
            position: relative;
            overflow: hidden;
            background-color: #000;
        }
        .target {
            position: absolute;
            border-radius: 50%;
            cursor: pointer;
            transition: opacity 0.15s, transform 0.1s;
            min-width: 30px;
            min-height: 30px;
            will-change: transform;
            user-select: none;
            -webkit-user-select: none;
        }
        .target.real {
            box-shadow: 0 0 15px 5px rgba(255,255,255,0.3);
        }
        .target.fake {
            border: 3px solid;
            background-color: transparent !important;
        }
        .target.decoy {
            opacity: 0.7;
        }
        #start-message, #end-message {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 48px;
            font-weight: bold;
            text-align: center;
            z-index: 100;
            color: white;
            text-shadow: 0 0 10px rgba(0,0,0,0.8);
            width: 100%;
        }
        #start-message {
            animation: pulse 1s infinite alternate;
        }
        @keyframes pulse {
            from { transform: translate(-50%, -50%) scale(1); }
            to { transform: translate(-50%, -50%) scale(1.1); }
        }
        .redirect-options {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 25px;
        }
        .redirect-btn {
            padding: 14px;
            border-radius: 8px;
            border: none;
            font-weight: bold;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .redirect-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .stats-container {
            background-color: rgba(0,0,0,0.7);
            padding: 15px;
            border-radius: 10px;
            margin-top: 15px;
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
        }
    </style>
</head>
<body>
    <div class="game-container">
        <div class="game-header">
            <div class="game-stat">Score: <span id="score">0</span></div>
            <div class="game-stat">Time: <span id="time">{{ GAME_DURATION }}</span></div>
            <div class="game-stat">Reaction: <span id="reaction">0</span>ms</div>
            <div class="game-stat">Speed: <span id="difficulty">1.0x</span></div>
        </div>
        <div id="game-area">
            <div id="start-message">3</div>
        </div>
    </div>

    <script>
        // Game config
        const CONFIG = {
            DURATION: {{ GAME_DURATION }},
            INIT_DELAY: {{ INITIAL_TARGET_DELAY }},
            MIN_DELAY: {{ MIN_TARGET_DELAY }},
            DIFF_RATE: {{ DIFFICULTY_INCREASE_RATE }},
            MAX_TARGETS: {{ MAX_TARGETS }},
            SIZE_REDUCTION: {{ TARGET_SIZE_REDUCTION }}
        };

        // Game state
        let state = {
            score: 0,
            timeLeft: CONFIG.DURATION,
            active: false,
            delay: CONFIG.INIT_DELAY,
            activeTargets: 0,
            reactions: []
        };

        // DOM elements
        const elements = {
            gameArea: document.getElementById('game-area'),
            scoreDisplay: document.getElementById('score'),
            timeDisplay: document.getElementById('time'),
            reactionDisplay: document.getElementById('reaction'),
            difficultyDisplay: document.getElementById('difficulty')
        };

        // Target types with weights
        const TARGET_TYPES = [
            { class: 'real', weight: 0.5, clickable: true, points: 30 },
            { class: 'fake', weight: 0.3, clickable: false, penalty: 5 },
            { class: 'decoy', weight: 0.2, clickable: false, penalty: 3 }
        ];

        // Start game countdown
        startCountdown();

        function startCountdown() {
            let count = 3;
            const countdownElement = document.getElementById('start-message');
            
            const countdownInterval = setInterval(() => {
                countdownElement.textContent = count > 0 ? count : "GO!";
                
                if (count <= 0) {
                    clearInterval(countdownInterval);
                    setTimeout(() => {
                        countdownElement.remove();
                        startGame();
                    }, 500);
                }
                count--;
            }, 1000);
        }

        function startGame() {
            state.active = true;
            createTarget();
            
            // Game timer
            const timer = setInterval(() => {
                state.timeLeft--;
                elements.timeDisplay.textContent = state.timeLeft;
                
                if (state.timeLeft <= 0) {
                    clearInterval(timer);
                    endGame();
                }
            }, 1000);
        }

        function createTarget() {
            if (!state.active || state.activeTargets >= CONFIG.MAX_TARGETS) return;
            
            state.activeTargets++;
            const target = document.createElement('div');
            target.className = 'target';
            
            // Select target type
            const type = getRandomTargetType();
            target.classList.add(type.class);
            
            // Dynamic sizing
            const size = Math.max(30, 80 - (state.timeLeft * CONFIG.SIZE_REDUCTION));
            target.style.width = target.style.height = `${size}px`;
            
            // Random position with edge buffer
            const pos = getRandomPosition(size);
            target.style.left = `${pos.x}px`;
            target.style.top = `${pos.y}px`;
            
            // Visual styling
            const color = getRandomColor();
            styleTarget(target, type, color);
            
            // Add to game
            elements.gameArea.appendChild(target);
            
            // Click handling
            setupTargetEvents(target, type, color);
            
            // Auto-remove if not clicked
            setTimeout(() => {
                if (target.parentNode) {
                    fadeOutAndRemove(target);
                    scheduleNextTarget();
                }
            }, type.class === 'real' ? 700 : 400);
        }

        function setupTargetEvents(target, type, color) {
            const appearTime = performance.now();
            
            target.addEventListener('click', () => {
                if (!state.active) return;
                
                // Visual feedback
                target.style.transform = 'scale(0.9)';
                
                if (type.clickable) {
                    const reactionTime = (performance.now() - appearTime).toFixed(1);
                    state.reactions.push(parseFloat(reactionTime));
                    
                    const points = Math.max(1, Math.floor(type.points - (reactionTime / 3)));
                    updateScore(points, reactionTime);
                } else {
                    updateScore(-type.penalty);
                }
                
                fadeOutAndRemove(target);
                increaseDifficulty();
                scheduleNextTarget();
            });
        }

        function updateScore(points, reactionTime = null) {
            state.score = Math.max(0, state.score + points);
            elements.scoreDisplay.textContent = state.score;
            
            if (reactionTime) {
                elements.reactionDisplay.textContent = reactionTime;
            }
        }

        function increaseDifficulty() {
            state.delay = Math.max(CONFIG.MIN_DELAY, state.delay * CONFIG.DIFF_RATE);
            elements.difficultyDisplay.textContent = `${(CONFIG.INIT_DELAY/state.delay).toFixed(1)}x`;
        }

        function scheduleNextTarget() {
            const targetsToCreate = Math.min(
                CONFIG.MAX_TARGETS - state.activeTargets,
                Math.floor(1 + (1 - state.delay/CONFIG.INIT_DELAY) * 2)
            );
            
            for (let i = 0; i < targetsToCreate; i++) {
                setTimeout(createTarget, i * (state.delay * 400));
            }
        }

        function endGame() {
            state.active = false;
            
            const avgReaction = state.reactions.length > 0 
                ? (state.reactions.reduce((a,b) => a + b, 0) / state.reactions.length).toFixed(1)
                : 0;
            
            showGameOver(state.score, avgReaction);
            saveScore(avgReaction);
        }

        function showGameOver(score, avgReaction) {
            elements.gameArea.innerHTML = `
                <div id="end-message">
                    <div style="color: #f39c12; font-size: 42px;">Game Over!</div>
                    <div style="margin: 15px 0; font-size: 32px; color: white;">Your Score: ${score}</div>
                    
                    <div class="stats-container">
                        <div class="stat-row">
                            <span>Average Reaction:</span>
                            <span>${avgReaction}ms</span>
                        </div>
                        <div class="stat-row">
                            <span>Targets Hit:</span>
                            <span>${state.reactions.length}</span>
                        </div>
                        <div class="stat-row">
                            <span>Final Speed:</span>
                            <span>${(CONFIG.INIT_DELAY/state.delay).toFixed(1)}x</span>
                        </div>
                    </div>
                    
                    <div class="redirect-options">
                        <button class="redirect-btn" onclick="window.location.href='https://ultraproadhyan.github.io/MY_web_game/home.html'" 
                            style="background: #3498db; color: white;">
                            🏠 Go to Home Page
                        </button>
                    </div>
                </div>
            `;
        }

        function saveScore(avgReaction) {
            fetch('/save_score', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: '{{ name }}',
                    phone: '{{ phone }}',
                    age: '{{ age }}',
                    score: state.score,
                    avg_reaction: avgReaction
                })
            });
        }

        // Helper functions
        function getRandomTargetType() {
            const rand = Math.random();
            let cumulativeWeight = 0;
            
            for (const type of TARGET_TYPES) {
                cumulativeWeight += type.weight;
                if (rand < cumulativeWeight) return type;
            }
            return TARGET_TYPES[0];
        }

        function getRandomPosition(size) {
            const padding = 15;
            return {
                x: padding + Math.random() * (elements.gameArea.offsetWidth - size - padding*2),
                y: padding + Math.random() * (elements.gameArea.offsetHeight - size - padding*2)
            };
        }

        function getRandomColor() {
            const colors = ['#FF5252', '#4CAF50', '#2196F3', '#FFEB3B', '#9C27B0', '#00BCD4'];
            return colors[Math.floor(Math.random() * colors.length)];
        }

        function styleTarget(target, type, color) {
            if (type.class === 'real') {
                target.style.backgroundColor = color;
            } else if (type.class === 'fake') {
                target.style.borderColor = color;
                target.style.backgroundColor = 'transparent';
            } else {
                target.style.backgroundColor = `${color}80`;
            }
        }

        function fadeOutAndRemove(target) {
            target.style.opacity = '0';
            target.style.transform = 'scale(1.1)';
            setTimeout(() => {
                if (target.parentNode) {
                    target.parentNode.removeChild(target);
                    state.activeTargets--;
                }
            }, 200);
        }

        // Enhanced touch handling for mobile
        elements.gameArea.addEventListener('touchstart', (e) => {
            if (e.target.classList.contains('target')) {
                e.preventDefault();
                const touch = e.touches[0];
                const clickEvent = new MouseEvent('click', {
                    clientX: touch.clientX,
                    clientY: touch.clientY
                });
                e.target.dispatchEvent(clickEvent);
            }
        }, { passive: false });
    </script>
</body>
</html>
"""

LEADERBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>🏆 Leaderboard 🏆</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root {
            --primary: #3498db; --danger: #e74c3c; --success: #2ecc71; 
            --warning: #f39c12; --dark: #111; --light: #222;
        }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: var(--dark);
            color: white;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: var(--warning);
            margin-bottom: 10px;
        }
        .leaderboard-container {
            background-color: var(--light);
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }
        .winner-card {
            background: linear-gradient(to right, #333, #2a2a2a);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 5px solid var(--warning);
            position: relative;
            overflow: hidden;
        }
        .winner-card::before {
            content: "🏆";
            position: absolute;
            right: 20px;
            top: 20px;
            font-size: 40px;
            opacity: 0.2;
        }
        .winner-title {
            font-size: 22px;
            font-weight: bold;
            margin-bottom: 10px;
            color: var(--warning);
        }
        .winner-info {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 10px;
        }
        .winner-stats {
            display: flex;
            justify-content: space-between;
            margin-top: 15px;
            font-size: 14px;
            color: #aaa;
        }
        .group-card {
            background-color: #2a2a2a;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            border: 1px solid #333;
        }
        .group-title {
            font-weight: bold;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 1px solid #444;
            font-size: 18px;
            color: var(--primary);
        }
        .player-row {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #333;
        }
        .player-row.header {
            font-weight: bold;
            border-bottom: 2px solid #444;
        }
        .player-name {
            font-weight: bold;
        }
        .player-score {
            color: var(--success);
            text-align: right;
        }
        .player-reaction {
            color: #aaa;
            text-align: right;
            font-size: 14px;
        }
        .back-btn {
            display: block;
            text-align: center;
            background-color: var(--warning);
            color: #000;
            padding: 14px;
            border-radius: 8px;
            text-decoration: none;
            font-weight: bold;
            font-size: 18px;
            margin-top: 30px;
            transition: all 0.3s;
        }
        .back-btn:hover {
            background-color: #ffc107;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .no-winners {
            text-align: center;
            padding: 40px 20px;
            font-size: 18px;
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏆 Ultimate Speed Challenge Leaderboard 🏆</h1>
        <p>Top performers from each group of 5 players</p>
    </div>
    
    <div class="leaderboard-container">
        {% if winners %}
            {% for winner in winners %}
                <div class="winner-card">
                    <div class="winner-title">Winner: {{ winner.name }}</div>
                    <div class="winner-info">
                        <div>Phone: {{ winner.phone }}</div>
                        <div>Age: {{ winner.age }}</div>
                        <div>Score: <strong>{{ winner.score }} points</strong></div>
                        <div>Reaction: {{ winner.reaction }}ms</div>
                    </div>
                    <div class="winner-stats">
                        <span>Group: {{ winner.group }}</span>
                        <span>Date: {{ winner.date }}</span>
                    </div>
                </div>
                
                <div class="group-card">
                    <div class="group-title">Group Performance ({{ winner.group }})</div>
                    <div class="player-row header">
                        <div>Player</div>
                        <div class="player-score">Score</div>
                        <div class="player-reaction">Reaction</div>
                    </div>
                    {% for player in winner.players %}
                        <div class="player-row">
                            <div class="player-name">{{ player.name }}</div>
                            <div class="player-score">{{ player.score }} pts</div>
                            <div class="player-reaction">{{ player.reaction }}ms</div>
                        </div>
                    {% endfor %}
                </div>
            {% endfor %}
        {% else %}
            <div class="no-winners">
                No winners yet! Be the first to top the leaderboard.
            </div>
        {% endif %}
        
        <a href="/" class="back-btn">Return to Game</a>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    position, remaining = get_player_position()
    return render_template_string(INDEX_HTML, position=position, remaining=remaining)

@app.route('/start', methods=['POST'])
def start_game():
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    age = request.form.get('age', '').strip()
    
    if not all([name, phone, age]) or not age.isdigit() or int(age) < 18:
        return redirect(url_for('index'))
    
    return render_template_string(
        GAME_HTML,
        name=name,
        phone=phone,
        age=age,
        GAME_DURATION=GAME_DURATION,
        INITIAL_TARGET_DELAY=INITIAL_TARGET_DELAY,
        MIN_TARGET_DELAY=MIN_TARGET_DELAY,
        DIFFICULTY_INCREASE_RATE=DIFFICULTY_INCREASE_RATE,
        MAX_TARGETS=MAX_TARGETS,
        TARGET_SIZE_REDUCTION=TARGET_SIZE_REDUCTION
    )

@app.route('/save_score', methods=['POST'])
def save_score():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Invalid request'}), 400
    
    data = request.get_json()
    required_fields = ['name', 'phone', 'age', 'score', 'avg_reaction']
    
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Missing data'}), 400
    
    try:
        save_player_data(
            data['name'],
            data['phone'],
            data['age'],
            data['score'],
            float(data['avg_reaction'])
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/leaderboard')
def leaderboard():
    winners = []
    if os.path.exists(WINNERS_FILE):
        try:
            with open(WINNERS_FILE, 'r') as f:
                groups = f.read().strip().split('-----\n')
                
                for i, group in enumerate(groups[::-1]):  # Show newest first
                    lines = [line for line in group.split('\n') if line.strip()]
                    if len(lines) < 2:
                        continue
                    
                    # Parse winner
                    winner_parts = lines[0].split('|')
                    winner = {
                        'name': winner_parts[0].replace('Winner: ', ''),
                        'phone': winner_parts[1].replace('Phone: ', ''),
                        'age': winner_parts[2].replace('Age: ', ''),
                        'score': winner_parts[3].replace('Score: ', ''),
                        'reaction': winner_parts[4].replace('Reaction: ', '').replace('ms', ''),
                        'group': f"Group {len(groups)-i}",
                        'date': datetime.now().strftime("%Y-%m-%d"),
                        'players': []
                    }
                    
                    # Parse players
                    for line in lines[1:]:
                        if line.startswith('Player: '):
                            parts = line.split('|')
                            winner['players'].append({
                                'name': parts[0].replace('Player: ', ''),
                                'phone': parts[1].replace('Phone: ', ''),
                                'age': parts[2].replace('Age: ', ''),
                                'score': parts[3].replace('Score: ', '').replace('pts', ''),
                                'reaction': parts[4].replace('Reaction: ', '').replace('ms', '')
                            })
                    
                    winners.append(winner)
        except Exception as e:
            print(f"Leaderboard error: {str(e)}")
    
    return render_template_string(LEADERBOARD_HTML, winners=winners)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)