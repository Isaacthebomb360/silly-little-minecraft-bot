// mineflayer_wrapper.js
const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals: { GoalBlock, GoalNear } } = require('mineflayer-pathfinder');
const readline = require('readline');
const mcData = require('minecraft-data');

const HOST = process.env.HOST || 'localhost';
const PORT = parseInt(process.env.PORT) || 25565;
const USERNAME = process.env.USERNAME || 'PythonBot';

const bot = mineflayer.createBot({ host: HOST, port: PORT, username: USERNAME });
bot.loadPlugin(pathfinder);

let defaultMove;
bot.once('spawn', () => {
    const data = mcData(bot.version);
    defaultMove = new Movements(bot, data);
    sendEvent({ event: 'spawn', message: 'Bot spawned!' });
});

function sendEvent(event) {
    console.log(JSON.stringify(event));
}

// Chat listener
bot.on('chat', (username, message) => {
    sendEvent({ event: 'chat', user: username, message });
});

// Helper: move to block
async function moveToBlock(pos) {
    bot.pathfinder.setMovements(defaultMove);
    bot.pathfinder.setGoal(new GoalBlock(pos.x, pos.y, pos.z));
    await bot.waitForTicks(20);
}

// Helper: place chest and dump items, supports multi-chest if inventory is full
async function placeChestAndDump() {
    let items = bot.inventory.items().filter(i => !i.name.includes('air'));
    if (!items.length) {
        bot.chat('Inventory empty, nothing to dump.');
        return;
    }

    while (items.length > 0) {
        const chestItem = bot.inventory.items().find(i => i.name.includes('chest'));
        if (!chestItem) {
            bot.chat('No chest in inventory!');
            return;
        }

        const posBelow = bot.entity.position.offset(0, -1, 0);
        const blockBelow = bot.blockAt(posBelow);
        if (!blockBelow || !bot.canPlaceBlock(blockBelow)) {
            bot.chat('Cannot place chest here.');
            return;
        }

        await bot.equip(chestItem, 'hand');
        await bot.placeBlock(blockBelow, bot.blockAt(posBelow));
        const chest = await bot.openChest(bot.blockAt(posBelow));

        for (const item of items) {
            await chest.deposit(item.type, null, item.count);
        }
        chest.close();

        items = bot.inventory.items().filter(i => !i.name.includes('air') && !i.name.includes('chest'));
        bot.chat('Placed chest and dumped items.');
    }
}

// Helper: follow a specific player
async function followPlayer(playerName) {
    const playerEntity = bot.players[playerName]?.entity;
    if (!playerEntity) {
        bot.chat(`Player ${playerName} not found.`);
        return;
    }
    bot.pathfinder.setMovements(defaultMove);
    bot.pathfinder.setGoal(new GoalNear(playerEntity.position.x, playerEntity.position.y, playerEntity.position.z, 1));
    bot.chat(`Following ${playerName}`);
}

// Command handlers
const rl = readline.createInterface({ input: process.stdin });

rl.on('line', async (line) => {
    try {
        const msg = JSON.parse(line);
        if (!msg.command) return;

        switch (msg.command) {
            case 'chat':
                if (msg.args.message) bot.chat(msg.args.message);
                break;

            case 'come':
                if (msg.args.position && defaultMove) {
                    await moveToBlock(msg.args.position);
                    bot.chat(`Coming to ${msg.args.position.x}, ${msg.args.position.y}, ${msg.args.position.z}`);
                }
                break;

            case 'jump':
                bot.setControlState('jump', true);
                setTimeout(() => bot.setControlState('jump', false), 500);
                bot.chat('🦘 Jumped!');
                break;

            case 'move':
                const dir = msg.args.direction;
                const controls = ['forward', 'back', 'left', 'right'];
                if (controls.includes(dir)) {
                    bot.setControlState(dir, true);
                    setTimeout(() => bot.setControlState(dir, false), 1000);
                    bot.chat(`Moved ${dir}`);
                }
                break;

            case 'pickup':
                const item = bot.nearestEntity(e => e.type === 'object' && e.objectType === 'item');
                if (item) {
                    bot.pathfinder.setGoal(new GoalNear(item.position.x, item.position.y, item.position.z, 1));
                    bot.chat(`Going to pick up ${item.name || 'item'}`);
                } else {
                    bot.chat('No items nearby.');
                }
                break;

            case 'chop':
                const block = bot.findBlock({ matching: b => b.name.includes('log'), maxDistance: 16 });
                if (block) {
                    await bot.dig(block);
                    bot.chat('Chopped a tree!');
                } else {
                    bot.chat('No trees nearby.');
                }
                break;

            case 'mine':
                const start = msg.args.start;
                const end = msg.args.end;
                if (start && end) {
                    const dx = Math.sign(end.x - start.x);
                    const dz = Math.sign(end.z - start.z);
                    let pos = { ...start };
                    while (pos.x !== end.x || pos.z !== end.z) {
                        const b = bot.blockAt(pos);
                        if (b && bot.canDigBlock(b)) await bot.dig(b);
                        if (pos.x !== end.x) pos.x += dx;
                        if (pos.z !== end.z) pos.z += dz;
                    }
                    bot.chat('Finished strip mining!');
                } else {
                    bot.chat('Invalid mine coordinates.');
                }
                break;
            case 'help':
                bot.chat(
                    `Commands: !hello, !status, !jump, !move <dir>, !come, !pickup, !chop, !mine x1 y1 z1 x2 y2 z2, !respawn, !chest, !follow <player>, !help`
                );
                break;
            case 'respawn':
                if (bot.health === 0) {
                    bot.chat('Respawning...');
                    bot.emit('respawn');
                } else {
                    bot.chat('I am still alive!');
                }
                break;

            case 'chest':
                await placeChestAndDump();
                break;

            case 'follow':
                if (msg.args.player) {
                    await followPlayer(msg.args.player);
                } else {
                    bot.chat('No player specified to follow.');
                }
                break;

            default:
                bot.chat(`Unknown command: ${msg.command}`);
        }

    } catch (err) {
        sendEvent({ event: 'error', message: err.toString() });
    }
});

// Error handling
bot.on('error', (err) => sendEvent({ event: 'error', message: err.toString() }));
bot.on('end', () => sendEvent({ event: 'end', message: 'Bot disconnected' }));
