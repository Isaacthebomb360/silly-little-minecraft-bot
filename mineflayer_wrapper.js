// mineflayer_wrapper.js
const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals: { GoalBlock } } = require('mineflayer-pathfinder');
const readline = require('readline');

const HOST = process.env.HOST || 'localhost';
const PORT = parseInt(process.env.PORT) || 25565;
const USERNAME = process.env.USERNAME || 'PythonBot';

const bot = mineflayer.createBot({
    host: HOST,
    port: PORT,
    username: USERNAME,
});

bot.loadPlugin(pathfinder);

// Send JSON messages to Python
function sendEvent(event) {
    console.log(JSON.stringify(event));
}

bot.once('spawn', () => {
    sendEvent({ event: 'spawn', message: 'Bot spawned!' });
});

// Listen for chat
bot.on('chat', (username, message) => {
    sendEvent({ event: 'chat', user: username, message: message });
});

// Handle stdin commands from Python
const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

rl.on('line', async (line) => {
    try {
        const msg = JSON.parse(line);
        if (!msg.command) return;

        if (msg.command === 'chat') {
            bot.chat(msg.args.message);
        } else if (msg.command === 'come') {
            const pos = msg.args.position;
            const mcData = require('minecraft-data')(bot.version);
            const defaultMove = new Movements(bot, mcData);
            bot.pathfinder.setMovements(defaultMove);
            bot.pathfinder.setGoal(new GoalBlock(pos.x, pos.y, pos.z));
            bot.chat(`Coming to ${pos.x}, ${pos.y}, ${pos.z}`);
        } else if (msg.command === 'jump') {
            bot.setControlState('jump', true);
            setTimeout(() => bot.setControlState('jump', false), 500);
            bot.chat('🦘 Jumped!');
        } else if (msg.command === 'move') {
            const dir = msg.args.direction;
            const controls = ['forward', 'back', 'left', 'right'];
            if (controls.includes(dir)) {
                bot.setControlState(dir, true);
                setTimeout(() => bot.setControlState(dir, false), 1000);
                bot.chat(`Moved ${dir}`);
            }
        }
    } catch (err) {
        sendEvent({ event: 'error', message: err.toString() });
    }
});

// Keep bot alive
bot.on('end', () => sendEvent({ event: 'end', message: 'Bot disconnected' }));
bot.on('error', (err) => sendEvent({ event: 'error', message: err.toString() }));
