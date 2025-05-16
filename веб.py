from flask import Flask, request, render_template_string
from telegram import Update, Bot, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import os

app = Flask(__name__)
TOKEN = "ВАШ_ТОКЕН_БОТА"  # Замените на токен @lemanpro_bot

# HTML-шаблон игры
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Fly Game</title>
    <meta charset="utf-8">
    <style>
        body { margin: 0; overflow: hidden; }
        #game { background: skyblue; }
        #score { position: fixed; top: 10px; left: 10px; font-size: 20px; }
    </style>
</head>
<body>
    <div id="score">Score: 0</div>
    <canvas id="game"></canvas>
    <script>
        const canvas = document.getElementById('game');
        const ctx = canvas.getContext('2d');
        
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const ball = {
            x: canvas.width/2,
            y: canvas.height/2,
            radius: 20,
            velocity: 0,
            gravity: 0.5,
            jump: -10
        };
        
        let score = 0;
        let isJumping = false;
        
        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Рисуем шарик
            ctx.beginPath();
            ctx.arc(ball.x, ball.y, ball.radius, 0, Math.PI*2);
            ctx.fillStyle = 'red';
            ctx.fill();
            ctx.closePath();
            
            // Обновляем счет
            document.getElementById('score').innerHTML = `Score: ${score}`;
            score++;
        }
        
        function update() {
            ball.velocity += ball.gravity;
            ball.y += ball.velocity;
            
            // Столкновение с границами
            if(ball.y + ball.radius > canvas.height) {
                gameOver();
            }
        }
        
        function gameOver() {
            Telegram.WebApp.sendData(JSON.stringify({score: score}));
        }
        
        function gameLoop() {
            update();
            draw();
            requestAnimationFrame(gameLoop);
        }
        
        // Управление
        canvas.addEventListener('touchstart', () => {
            ball.velocity = ball.jump;
        });
        
        // Инициализация WebApp
        Telegram.WebApp.ready();
        gameLoop();
    </script>
</body>
</html>
"""

@app.route('/')
def web_app():
    return render_template_string(HTML_TEMPLATE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(
        "🎮 Играть в Fly!",
        web_app=WebAppInfo(url=f"https://ВАШ_ХОСТ/")
    )]]
    await update.message.reply_text(
        "Добро пожаловать в игру Fly!\nНажмите кнопку чтобы начать:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = json.loads(update.message.web_app_data.data)
    await update.message.reply_text(f"🏆 Ваш результат: {data['score']} очков!")

if __name__ == '__main__':
    # Инициализация бота
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    
    # Запуск Flask в отдельном потоке
    from threading import Thread
    Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000}).start()
    
    # Запуск бота
    application.run_polling()
