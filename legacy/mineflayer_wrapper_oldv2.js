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

// Utility: material priority for armor/weapons
const MATERIAL_PRIORITY = ['netherite', 'diamond', 'iron', 'chainmail', 'gold', 'leather'];

// Find best item matching slot by name heuristics
function findBestArmorItemForSlot(slot) {
    // slot: 'head', 'torso', 'legs', 'feet' -> map to name parts
    const slotNames = {
        head: ['helmet', 'head'],
        torso: ['chestplate', 'chest'],
        legs: ['leggings', 'legs'],
        feet: ['boots', 'feet']
    };
    const names = slotNames[slot];

    // Gather candidates
    const candidates = bot.inventory.items().filter(it => {
        const nm = it.name.toLowerCase();
        return names.some(n => nm.includes(n));
    });

    // Sort by material priority
    candidates.sort((a, b) => {
        const an = a.name.toLowerCase();
        const bn = b.name.toLowerCase();
        const aIndex = MATERIAL_PRIORITY.findIndex(m => an.includes(m));
        const bIndex = MATERIAL_PRIORITY.findIndex(m => bn.includes(m));
        return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
    });

    return candidates.length ? candidates[0] : null;
}

async function equipBestArmor() {
    try {
        // Map slots to mineflayer equip positions
        const slotMap = [
            { name: 'head', equipSlot: 'head' },
            { name: 'torso', equipSlot: 'torso' },
            { name: 'legs', equipSlot: 'legs' },
            { name: 'feet', equipSlot: 'feet' },
        ];

        for (const s of slotMap) {
            const item = findBestArmorItemForSlot(s.name);
            if (item) {
                try {
                    await bot.equip(item, s.equipSlot);
                    bot.chat(`Equipped ${item.name} in ${s.equipSlot}`);
                } catch (e) {
                    bot.chat(`Couldn't equip ${item.name}: ${e.message}`);
                }
            }
        }
    } catch (err) {
        bot.chat(`Error during equip: ${err.message}`);
    }
}

// Find best weapon (prefer swords, then axes) by material priority
function findBestWeapon() {
    const items = bot.inventory.items();
    const weaponCandidates = items.filter(it => {
        const n = it.name.toLowerCase();
        return n.includes('sword') || n.includes('axe');
    });

    weaponCandidates.sort((a, b) => {
        const an = a.name.toLowerCase();
        const bn = b.name.toLowerCase();
        const aIndex = MATERIAL_PRIORITY.findIndex(m => an.includes(m));
        const bIndex = MATERIAL_PRIORITY.findIndex(m => bn.includes(m));
        return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
    });

    return weaponCandidates.length ? weaponCandidates[0] : null;
}

async function placeChestAndDump() {
    const botPos = bot.entity.position.floored();
    const below = bot.blockAt(botPos.offset(0, -1, 0));
    const nearbyChest = bot.findBlock({
        matching: block => block.name.includes('chest'),
        maxDistance: 3
    });

    //de-equip any held items
    try {
        await bot.equip(null, 'hand');
        await bot.equip(null, 'off-hand');
        await bot.equip(null, 'head');
        await bot.equip(null, 'chest');
        await bot.equip(null, 'legs');
        await bot.equip(null, 'feet');
    } catch (e) {
        // ignore
    }

    let chestBlock = null;

    // ✅ 1. Prefer chest below you or nearby
    if (below && below.name.includes('chest')) {
        bot.chat('Standing on a chest, using it for deposit.');
        chestBlock = below;
    } else if (nearbyChest) {
        bot.chat(`Using nearby chest at ${nearbyChest.position.x}, ${nearbyChest.position.y}, ${nearbyChest.position.z}.`);
        chestBlock = nearbyChest;
    } else {
        bot.chat('No chest nearby, Please place a chest within 3 blocks.');
        return;
    }

    // ✅ 3. Deposit items into the chest
    if (!chestBlock) {
        bot.chat('Could not find or place a chest.');
        return;
    }

    // pathfind to chest
    try {
        bot.pathfinder.setMovements(defaultMove);
        bot.pathfinder.setGoal(new GoalNear(chestBlock.position.x, chestBlock.position.y, chestBlock.position.z, 1));
    } catch (err) {
        bot.chat(`Error pathfinding to chest: ${err.message}`);
        return;
    }

    try {
        const chest = await bot.openChest(chestBlock);
        const items = bot.inventory.items().filter(i => !i.name.includes('air') && !i.name.includes('chest'));

        if (items.length === 0) {
            bot.chat('Inventory empty, nothing to deposit.');
            chest.close();
            return;
        }

        for (const item of items) {
            try {
                await chest.deposit(item.type, null, item.count);
                bot.chat(`Deposited ${item.name} x${item.count}`);
            } catch (err) {
                bot.chat(`Failed to deposit ${item.name}: ${err.message}`);
            }
        }

        chest.close();
        bot.chat('✅ All items deposited successfully.');
    } catch (err) {
        bot.chat(`Error interacting with chest: ${err.message}`);
    }
}

// FOLLOW & COME already exist in your code; ensure stop works to clear intervals
// We'll store intervals on bot.followInterval and bot.defendInterval

// Helper: continuous follow (replaces earlier lighter version)
function startFollowing(targetName) {
    if (bot.followInterval) {
        clearInterval(bot.followInterval);
    }

    bot.chat(`Following ${targetName}...`);
    bot.pathfinder.setMovements(defaultMove);

    bot.followInterval = setInterval(() => {
        const player = bot.players[targetName]?.entity;
        if (!player) {
            bot.chat(`${targetName} disappeared! Stopping follow.`);
            bot.pathfinder.stop();
            clearInterval(bot.followInterval);
            bot.followInterval = null;
            return;
        }
        bot.pathfinder.setGoal(new GoalNear(player.position.x, player.position.y, player.position.z, 1));
    }, 1000);
}

// Helper: single come
async function comeToPlayer(targetName) {
    const playerEntity = bot.players[targetName]?.entity;
    if (!playerEntity) {
        bot.chat(`Can't find ${targetName}`);
        return;
    }
    bot.pathfinder.setMovements(defaultMove);
    bot.pathfinder.setGoal(new GoalNear(playerEntity.position.x, playerEntity.position.y, playerEntity.position.z, 1));
    bot.chat(`Coming to you, ${targetName}!`);
}

// DEFEND logic: keeps attacking nearest mob and auto equips best weapon and armor
function startDefending() {
    if (bot.defendInterval) {
        bot.chat('Already defending.');
        return;
    }

    bot.chat('Entering defense mode!');

    // Equip best armor first
    equipBestArmor();

    bot.defendInterval = setInterval(async () => {
        try {
            // Find nearest mob (exclude players)
            const mobs = Object.values(bot.entities).filter(e => e && e.type === 'mob' && e.position && e.mobType !== undefined);
            if (!mobs.length) {
                // no mobs nearby
                return;
            }

            // pick closest
            mobs.sort((a, b) => bot.entity.position.distanceTo(a.position) - bot.entity.position.distanceTo(b.position));
            const target = mobs[0];

            if (!target || !target.position) return;

            const dist = bot.entity.position.distanceTo(target.position);
            // If too far (>20) skip
            if (dist > 30) return;

            // Equip best weapon
            const weapon = findBestWeapon();
            if (weapon) {
                try { await bot.equip(weapon, 'hand'); } catch (e) { }
            }

            // Move into range
            bot.pathfinder.setMovements(defaultMove);
            bot.pathfinder.setGoal(new GoalNear(target.position.x, target.position.y, target.position.z, 1));

            // Attack if in range
            if (bot.entity.position.distanceTo(target.position) <= 3) {
                try {
                    bot.attack(target);
                    // small cooldown
                    await new Promise(r => setTimeout(r, 600));
                } catch (e) {
                    // fallback: use arm swing chat
                }
            }
        } catch (err) {
            // ignore per-iteration errors
        }
    }, 800); // check ~ every 0.8s
}

function stopAllIntervals() {
    if (bot.followInterval) {
        clearInterval(bot.followInterval);
        bot.followInterval = null;
    }
    if (bot.defendInterval) {
        clearInterval(bot.defendInterval);
        bot.defendInterval = null;
    }
    bot.pathfinder.stop();
    bot.chat('Stopped active behaviors.');
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
                if (msg.args.player && defaultMove) {
                    await comeToPlayer(msg.args.player);
                } else {
                    bot.chat('No target specified for come.');
                }
                break;
            case 'jump':
                bot.setControlState('jump', true);
                setTimeout(() => bot.setControlState('jump', false), 500);
                bot.chat('Jumped!');
                break;
            case 'move':
                {
                    const dir = msg.args.direction;
                    const controls = ['forward', 'back', 'left', 'right'];
                    if (controls.includes(dir)) {
                        bot.setControlState(dir, true);
                        setTimeout(() => bot.setControlState(dir, false), 1000);
                        bot.chat(`Moved ${dir}`);
                    }
                }
                break;
            case 'pickup':
                {
                    const item = bot.nearestEntity(e => e.type === 'object' && e.objectType === 'item');
                    if (item) {
                        bot.pathfinder.setGoal(new GoalNear(item.position.x, item.position.y, item.position.z, 1));
                        bot.chat(`Going to pick up item`);
                    } else {
                        bot.chat('No items nearby.');
                    }
                }
                break;
            case 'chop':
                {
                    const block = bot.findBlock({ matching: b => b.name.includes('log'), maxDistance: 16 });
                    if (block) {
                        await bot.dig(block);
                        bot.chat('Chopped a tree!');
                    } else {
                        bot.chat('No trees nearby.');
                    }
                }
                break;
            case 'mine':
                {
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
                }
                break;
            case 'help':
                bot.chat(
                    `Commands: !hello, !status, !jump, !move <dir>, !come, !pickup, !chop, !mine x1 y1 z1 x2 y2 z2, !respawn, !chest, !follow <player>, !follow, !follow-me, !stop, !deforest, !equip, !defend`
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
                    startFollowing(msg.args.player);
                } else {
                    bot.chat('No player specified to follow.');
                }
                break;
            case 'stop':
                stopAllIntervals();
                break;
            case 'deforest':
                // your existing deforest implementation could be used here; keep it as-is if you added it earlier
                // We'll implement a similar simple version:
                {
                    bot.chat('Starting deforestation... 🌲');

                    const logs = bot.findBlocks({
                        matching: (block) =>
                            block.name.includes('log') && !block.name.includes('stripped'),
                        maxDistance: 20,
                        count: 999,
                    });

                    if (!logs.length) {
                        bot.chat('No unstripped logs found nearby.');
                        break;
                    }

                    let choppedCount = 0;

                    async function chopNext() {
                        if (logs.length === 0) {
                            bot.chat(`Finished deforesting! 🌳 Total chopped: ${choppedCount}`);
                            return;
                        }

                        const pos = logs.shift();
                        const block = bot.blockAt(pos);

                        if (!block || !bot.canDigBlock(block)) {
                            setTimeout(chopNext, 100);
                            return;
                        }

                        try {
                            bot.pathfinder.setMovements(defaultMove);
                            bot.pathfinder.setGoal(new GoalNear(pos.x, pos.y, pos.z, 1));
                            await bot.waitForTicks(20);
                            await bot.dig(block);
                            choppedCount++;

                            if (choppedCount % 5 === 0) {
                                bot.chat(`Chopped ${choppedCount} logs so far...`);
                            }

                            setTimeout(chopNext, 200);
                        } catch (err) {
                            bot.chat(`Error chopping: ${err.message}`);
                            setTimeout(chopNext, 200);
                        }
                    }

                    chopNext();
                }
                break;
            case 'follow-me': // optional: a convenience alias
                if (msg.args.player) startFollowing(msg.args.player);
                break;
            case 'equip':
                await equipBestArmor();
                break;
            case 'defend':
                startDefending();
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
