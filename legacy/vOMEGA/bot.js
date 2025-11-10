// bot.js
const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals: { GoalNear } } = require('mineflayer-pathfinder');
const mcData = require('minecraft-data')(bot.version) // <- must match server

const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

// Config via env or defaults
const host = process.env.MC_HOST || 'localhost';
const port = parseInt(process.env.MC_PORT || '25565', 10);
const username = process.env.MC_USERNAME || 'BotFromPython';
const auth = process.env.MC_AUTH || 'offline';

const bot = mineflayer.createBot({
    host: host,
    port: port,
    username: username,
    auth: auth
});

bot.loadPlugin(pathfinder);

function sendEvent(obj) {
    process.stdout.write(JSON.stringify(obj) + '\n');
}

bot.once('spawn', () => {
    bot.loadPlugin(pathfinder);
    const defaultMove = new Movements(bot, mcData);
    bot.pathfinder.setMovements(defaultMove);

    sendEvent({ type: 'spawn', message: 'Bot spawned' });
    // Optionally greet
    bot.chat('Hello! Bot ready.');
});

bot.on('chat', (username, message) => {
    if (username === bot.username) return;
    sendEvent({ type: 'chat', user: username, message: message });
});

bot.on('error', err => {
    sendEvent({ type: 'error', error: err.toString() });
});

bot.on('kicked', reason => {
    sendEvent({ type: 'kicked', reason: reason.toString() });
});

// Read commands from Python
rl.on('line', line => {
    let cmd;
    try {
        cmd = JSON.parse(line);
    } catch (e) {
        return;
    }
    handleCommand(cmd);
});

async function handleCommand(cmd) {
    try {
        if (cmd.type === 'chat') {
            bot.chat(cmd.message);
            sendEvent({ type: 'ok', id: cmd.id || null });
        }
        else if (cmd.type === 'follow') {
            const player = bot.players[cmd.player];
            if (!player || !player.entity) {
                sendEvent({ type: 'error', message: 'player_not_found', id: cmd.id || null });
                return;
            }
            const p = player.entity.position;
            const moves = new Movements(bot);
            bot.pathfinder.setMovements(moves);
            bot.pathfinder.setGoal(new GoalNear(p.x, p.y, p.z, 1));
            sendEvent({ type: 'ok', id: cmd.id || null });
        }
        else if (cmd.type === 'stop') {
            bot.pathfinder.setGoal(null);
            sendEvent({ type: 'ok', id: cmd.id || null });
        }
        else {
            sendEvent({ type: 'error', message: 'unknown_command', id: cmd.id || null });
        }
    } catch (err) {
        sendEvent({ type: 'error', message: err.toString(), id: cmd.id || null });
    }
}
