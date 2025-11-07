// mineflayer_wrapper.js
const fs = require('fs');
const path = require('path');
const mineflayer = require('mineflayer');
const { pathfinder, Movements, goals: { GoalBlock, GoalNear } } = require('mineflayer-pathfinder');
const readline = require('readline');
const mcData = require('minecraft-data');
const Vec3 = require('vec3');

const HOME_FILE = path.join(__dirname, 'bot_home.json');

const HOST = process.env.HOST || 'localhost';
const PORT = parseInt(process.env.PORT) || 25565;
const USERNAME = process.env.USERNAME || 'PythonBot';

const bot = mineflayer.createBot({ host: HOST, port: PORT, username: USERNAME });
bot.loadPlugin(pathfinder);

let autoMode = false;
let autoInterval = null;

let defaultMove;
bot.once('spawn', () => {
    const data = mcData(bot.version);
    bot.chat('Hello world!');
    defaultMove = new Movements(bot, data);
    sendEvent({ event: 'spawn', message: 'Bot spawned!' });
    loadHome();
    bot.chat('Boot Up complete! Ready for commands!');
});

function sendEvent(event) {
    console.log(JSON.stringify(event));
}

// -----------------------------
// Persistence: home chest
// -----------------------------
let homeChest = null; // {x,y,z,world?}

function saveHome() {
    try {
        fs.writeFileSync(HOME_FILE, JSON.stringify(homeChest || null, null, 2), 'utf8');
        bot.chat('Home chest saved.');
    } catch (e) {
        bot.chat(`Failed to save home: ${e.message}`);
    }
}

function loadHome() {
    try {
        if (fs.existsSync(HOME_FILE)) {
            const data = JSON.parse(fs.readFileSync(HOME_FILE, 'utf8'));
            if (data && typeof data.x === 'number') {
                homeChest = data;
                bot.chat(`Loaded home chest at ${homeChest.x}, ${homeChest.y}, ${homeChest.z}`);
            }
        }
    } catch (e) {
        bot.chat(`Error loading home: ${e.message}`);
    }
}

// -----------------------------
// Utilities: inventory, armor, weapons
// -----------------------------
const MATERIAL_PRIORITY = ['netherite', 'diamond', 'iron', 'chainmail', 'gold', 'leather'];

function findBestArmorItemForSlot(slot) {
    const slotNames = {
        head: ['helmet', 'head'],
        torso: ['chestplate', 'chest'],
        legs: ['leggings', 'legs'],
        feet: ['boots', 'feet']
    };
    const names = slotNames[slot];
    const candidates = bot.inventory.items().filter(it => {
        const nm = it.name.toLowerCase();
        return names.some(n => nm.includes(n));
    });
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

function findBestWeapon() {
    const items = bot.inventory.items();
    const weaponCandidates = items.filter(it => {
        const n = it.name.toLowerCase();
        return n.includes('sword') || n.includes('axe') || n.includes('trident');
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

// -----------------------------
// Chest deposit helpers
// -----------------------------
async function openChestAt(block) {
    try {
        return await bot.openChest(block);
    } catch (e) {
        // sometimes openChest fails due to range/lag — try pathing closer then open
        try {
            bot.pathfinder.setMovements(defaultMove);
            bot.pathfinder.setGoal(new GoalNear(block.position.x, block.position.y, block.position.z, 1));
            await bot.waitForTicks(20);
            return await bot.openChest(block);
        } catch (err) {
            throw err;
        }
    }
}

async function depositAllIntoBlockChest(block) {
    try {
        const chest = await openChestAt(block);
        const items = bot.inventory.items().filter(i => !i.name.includes('air') && !i.name.includes('chest'));
        if (!items.length) {
            chest.close();
            bot.chat('Inventory empty, nothing to deposit.');
            return true;
        }
        for (const item of items) {
            try {
                await chest.deposit(item.type, null, item.count);
            } catch (err) {
                bot.chat(`Couldn't deposit ${item.name}: ${err.message}`);
            }
        }
        chest.close();
        bot.chat('Deposited items into chest.');
        return true;
    } catch (err) {
        bot.chat(`Failed to deposit into chest: ${err.message}`);
        return false;
    }
}

// Try deposit into home chest if set and reachable
async function depositToHomeChestIfSet() {
    if (!homeChest) return false;
    const b = bot.blockAt(homeChest);
    if (!b) {
        bot.chat('Saved home chest not found at coordinates.');
        return false;
    }
    // path to home chest then deposit
    try {
        bot.pathfinder.setMovements(defaultMove);
        bot.pathfinder.setGoal(new GoalNear(b.position.x, b.position.y, b.position.z, 1));
        await bot.waitForTicks(20);
        return await depositAllIntoBlockChest(b);
    } catch (e) {
        bot.chat(`Failed to deposit to home chest: ${e.message}`);
        return false;
    }
}

// Main chest command: use chest under/near bot, otherwise try home chest if set
async function placeChestAndDump() {
    const botPos = new Vec3(
        bot.entity.position.x,
        bot.entity.position.y,
        bot.entity.position.z
    );

    const below = bot.blockAt(botPos.offset(0, -1, 0));
    const nearbyChest = bot.findBlock({
        matching: block => block && block.name && block.name.includes('chest'),
        maxDistance: 4
    });

    // Case 1: Chest directly below
    if (below && below.name.includes('chest')) {
        await depositAllIntoBlockChest(below);
        return;
    }

    // Case 2: Nearby chest
    if (nearbyChest) {
        bot.chat(`Going to nearby chest at ${nearbyChest.position.x},${nearbyChest.position.y},${nearbyChest.position.z}`);
        bot.pathfinder.setMovements(defaultMove);
        bot.pathfinder.setGoal(new GoalNear(
            new Vec3(nearbyChest.position.x, nearbyChest.position.y, nearbyChest.position.z),
            1
        ));
        await bot.waitForTicks(20);
        await depositAllIntoBlockChest(nearbyChest);
        return;
    }

    // Case 3: Saved home chest
    if (homeChest) {
        bot.chat('No chest nearby, attempting to deposit to saved home chest...');
        const ok = await depositToHomeChestIfSet(); // Make sure this uses Vec3 as well
        if (ok) return;
        bot.chat('Could not deposit to saved home chest.');
        return;
    }

    bot.chat('No chest found nearby and no accessible home chest. Place a chest or use !sethome while standing on/next to a chest.');
}

// -----------------------------
// sethome / home handlers
// -----------------------------
async function setHomeAtNearbyChest() {
    const botPos = new Vec3(
        bot.entity.position.x,
        bot.entity.position.y,
        bot.entity.position.z
    );
    const below = bot.blockAt(botPos.offset(0, -1, 0));

    const nearbyChest = bot.findBlock({
        matching: b => b && b.name && b.name.includes('chest'),
        maxDistance: 3
    });

    let chestBlock = null;
    if (below && below.name.includes('chest')) chestBlock = below;
    else if (nearbyChest) chestBlock = nearbyChest;

    if (!chestBlock) {
        bot.chat('No chest under/near you to set as home. Stand on/next to the chest and run !sethome.');
        return;
    }

    homeChest = new Vec3(
        chestBlock.position.x,
        chestBlock.position.y,
        chestBlock.position.z
    );
    saveHome(); // Make sure this serializes homeChest correctly
    bot.chat(`Home chest set at ${homeChest.x}, ${homeChest.y}, ${homeChest.z}`);
}

async function goHomeAndDeposit() {
    if (!homeChest) {
        bot.chat('No home chest set. Use !sethome while standing by a chest.');
        return;
    }
    // Ensure homeChest is Vec3
    const homePos = new Vec3(homeChest.x, homeChest.y, homeChest.z);
    const block = bot.blockAt(homePos);
    if (!block || !block.name.includes('chest')) {
        bot.chat('Saved home chest not found at those coordinates.');
        return;
    }
    bot.chat('Going to home chest to deposit...');
    bot.pathfinder.setMovements(defaultMove);
    bot.pathfinder.setGoal(new GoalNear(block.position.x, block.position.y, block.position.z, 1));
    await bot.waitForTicks(20);
    await depositAllIntoBlockChest(block);
}

// -----------------------------
// follow / come already implemented
// -----------------------------
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

// -----------------------------
// deforest (50 block radius) - walk through all found logs
// -----------------------------
async function deforest(radius = 50) {
    bot.chat(`Scanning for unstripped logs within ${radius} blocks...`);
    // findBlocks returns array of Vec3 positions
    const logs = bot.findBlocks({
        matching: (block) => block && block.name && block.name.includes('log') && !block.name.includes('stripped'),
        maxDistance: radius,
        count: 2000
    });

    if (!logs || !logs.length) {
        bot.chat('No unstripped logs found nearby.');
        return;
    }

    // Sort by distance (closest first)
    logs.sort((a, b) => {
        const da = bot.entity.position.distanceTo(a);
        const db = bot.entity.position.distanceTo(b);
        return da - db;
    });

    bot.chat(`Found ${logs.length} log blocks. Beginning deforesting...`);

    let choppedCount = 0;
    const inventoryLimit = 27; // conservative "full" threshold (hotbar+inventory check)
    for (const pos of logs) {
        // check inventory fullness
        const freeSlots = bot.inventory.emptySlotCount();
        if (freeSlots <= 6) { // near-full -> try deposit
            bot.chat('Inventory low — attempting to deposit to home chest if set...');
            const deposited = await depositToHomeChestIfSet();
            if (!deposited) {
                bot.chat('No home chest available; stopping deforest to avoid losing items.');
                return;
            }
        }

        const block = bot.blockAt(pos);
        if (!block) continue;
        if (!bot.canDigBlock(block)) continue;

        try {
            bot.pathfinder.setMovements(defaultMove);
            bot.pathfinder.setGoal(new GoalNear(pos.x, pos.y, pos.z, 1));
            // wait to get there
            await bot.waitForTicks(20);
            // double-check block still exists and can be dug
            const current = bot.blockAt(pos);
            if (!current || !bot.canDigBlock(current)) continue;
            await bot.dig(current);
            choppedCount++;
            if (choppedCount % 10 === 0) bot.chat(`Chopped ${choppedCount} logs...`);
            // small delay
            await new Promise(r => setTimeout(r, 200));
        } catch (err) {
            bot.chat(`Error chopping at ${pos.x},${pos.y},${pos.z}: ${err.message}`);
            // continue with next block
        }
    }

    bot.chat(`Finished deforesting. Total chopped: ${choppedCount}`);
}

// ------------------------------
// Farming
// ------------------------------
async function farmCrops(radius = 16) {
    const crops = bot.findBlocks({
        matching: block => {
            if (!block) return false;
            const name = block.name.toLowerCase();
            // only mature crops
            return (
                (name.includes('wheat') && block.metadata === 7) ||
                (name.includes('carrot') && block.metadata === 7) ||
                (name.includes('potato') && block.metadata === 7) ||
                (name.includes('beetroot') && block.metadata === 7)
            );
        },
        maxDistance: radius,
        count: 999
    });

    if (!crops.length) {
        bot.chat('No mature crops found nearby.');
        return;
    }

    bot.chat(`Found ${crops.length} mature crops. Starting farming...`);

    for (const pos of crops) {
        const block = bot.blockAt(pos);
        if (!block) continue;

        try {
            // Move close
            bot.pathfinder.setGoal(new GoalNear(pos.x, pos.y, pos.z, 1));
            await bot.waitForTicks(10);
            await bot.dig(block);

            // Attempt to replant
            let seedItem = null;
            if (block.name.includes('wheat')) seedItem = bot.inventory.items().find(i => i.name.includes('wheat_seeds'));
            if (block.name.includes('carrot')) seedItem = bot.inventory.items().find(i => i.name.includes('carrot'));
            if (block.name.includes('potato')) seedItem = bot.inventory.items().find(i => i.name.includes('potato'));
            if (block.name.includes('beetroot')) seedItem = bot.inventory.items().find(i => i.name.includes('beetroot'));

            if (seedItem) {
                await bot.equip(seedItem, 'hand');
                await bot.placeBlock(bot.blockAt(pos.offset(0, -1, 0)), Vec3(0, 1, 0)); // plant on soil
            }

        } catch (err) {
            bot.chat(`Error farming at ${pos.x},${pos.y},${pos.z}: ${err.message}`);
        }
    }

    bot.chat('✅ Farming complete!');
}

// ------------------------------
// mining
// ------------------------------
async function stripMineArea(startPos, endPos, onlyOres = false) {
    bot.chat(`Starting strip mine from ${startPos.x},${startPos.y},${startPos.z} to ${endPos.x},${endPos.y},${endPos.z}`);

    const dx = Math.sign(endPos.x - startPos.x);
    const dy = Math.sign(endPos.y - startPos.y);
    const dz = Math.sign(endPos.z - startPos.z);

    let pos = startPos.clone();

    while (true) {
        const block = bot.blockAt(pos);
        if (block && bot.canDigBlock(block)) {
            if (!onlyOres || (onlyOres && block.name.includes('ore'))) {
                try {
                    bot.pathfinder.setGoal(new GoalNear(pos.x, pos.y, pos.z, 1));
                    await bot.waitForTicks(5);
                    await bot.dig(block);
                } catch (err) {
                    bot.chat(`Error mining at ${pos.x},${pos.y},${pos.z}: ${err.message}`);
                }
            }
        }

        // Move pos
        if (pos.x !== endPos.x) pos.x += dx;
        else if (pos.y !== endPos.y) pos.y += dy;
        else if (pos.z !== endPos.z) pos.z += dz;
        else break; // done
    }

    bot.chat('✅ Strip mining complete!');
}

// -----------------------------
// defend / combat improvements
// -----------------------------
function isHostileEntity(entity) {
    if (!entity || !entity.mobType) return false;
    const hostileNames = [
        'zombie', 'skeleton', 'creeper', 'spider', 'husk', 'drowned',
        'wither_skeleton', 'stray', 'witch', 'enderman', 'pillager',
        'vindicator', 'evoker', 'vex', 'slime', 'magmacube', 'blaze', 'ghast'
    ];
    const name = (entity.mobType || '').toString().toLowerCase();
    return hostileNames.some(h => name.includes(h));
}

function startDefending() {
    if (bot.defendInterval) {
        bot.chat('Already in defense mode.');
        return;
    }

    bot.chat('Entering defense mode: I will engage nearby hostile mobs.');

    // continuous loop
    bot.defendInterval = setInterval(async () => {
        try {
            // Equip best armor occasionally
            await equipBestArmor();

            // collect hostile mobs within 40 blocks
            const mobs = Object.values(bot.entities)
                .filter(e => e && e.type === 'mob' && e.position && isHostileEntity(e))
                .map(e => e)
                .sort((a, b) => bot.entity.position.distanceTo(a.position) - bot.entity.position.distanceTo(b.position));

            if (!mobs.length) return;

            const target = mobs[0];
            const dist = bot.entity.position.distanceTo(target.position);

            // if target too far, skip
            if (dist > 50) return;

            // equip best weapon
            const weapon = findBestWeapon();
            if (weapon) {
                try { await bot.equip(weapon, 'hand'); } catch (e) { }
            }

            // approach target
            bot.pathfinder.setMovements(defaultMove);
            bot.pathfinder.setGoal(new GoalNear(target.position.x, target.position.y, target.position.z, 1));

            // when in melee range, attack
            if (bot.entity.position.distanceTo(target.position) <= 3.5) {
                try {
                    bot.attack(target);
                } catch (e) {
                    // ignore attack errors
                }
            }

            // If bot health low, retreat to home if available
            if (bot.health && bot.health < 6) {
                bot.chat('Low health — attempting to retreat.');
                if (homeChest) {
                    const block = bot.blockAt(homeChest);
                    if (block) {
                        bot.pathfinder.setGoal(new GoalNear(block.position.x, block.position.y, block.position.z, 1));
                        await bot.waitForTicks(40);
                    }
                } else {
                    // try to run away — move backward for a bit
                    bot.setControlState('back', true);
                    await new Promise(r => setTimeout(r, 2000));
                    bot.setControlState('back', false);
                }
            }
        } catch (err) {
            // ignore per-iteration issues
        }
    }, 700);
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

// automated stuff
async function depositAllExceptTools() {
    if (!homeChest) {
        bot.chat("No home chest set! Use !sethome while standing on a chest.");
        return;
    }
    const homePos = new Vec3(homeChest.x, homeChest.y, homeChest.z);
    const chestBlock = bot.blockAt(homePos);
    if (!chestBlock || !chestBlock.name.includes('chest')) {
        bot.chat("Home chest not found at saved location.");
        return;
    }

    bot.pathfinder.setMovements(defaultMove);
    bot.pathfinder.setGoal(new GoalNear(homePos.x, homePos.y, homePos.z, 1));
    await bot.waitForTicks(20);

    try {
        const chest = await bot.openChest(chestBlock);
        const items = bot.inventory.items().filter(
            i => !i.name.includes('pickaxe') && !i.name.includes('axe') && !i.name.includes('hoe')
        );

        for (const item of items) {
            try { await chest.deposit(item.type, null, item.count); } catch (e) { }
        }
        chest.close();
        bot.chat("Deposited all non-tool items to home chest ✅");
    } catch (err) {
        bot.chat(`Error depositing to home chest: ${err.message}`);
    }
}

// -------------------
// AUTO MODE TASKS
// -------------------
async function autoTasks() {
    while (autoMode) {
        try {
            // 1️⃣ Chop Trees
            const logs = bot.findBlocks({
                matching: b => b && b.name.includes('log') && !b.name.includes('stripped'),
                maxDistance: 50,
                count: 999
            });
            if (logs.length) {
                bot.chat(`Chopping ${logs.length} logs...`);
                for (const pos of logs) {
                    const block = bot.blockAt(pos);
                    if (!block || !bot.canDigBlock(block)) continue;
                    bot.pathfinder.setGoal(new GoalNear(pos.x, pos.y, pos.z, 1));
                    await bot.waitForTicks(10);
                    await bot.dig(block);
                    if (bot.inventory.items().length > 28) {
                        await depositAllExceptTools();
                    }
                }
            }

            // 2️⃣ Farm crops
            const crops = bot.findBlocks({
                matching: b => {
                    if (!b) return false;
                    const name = b.name.toLowerCase();
                    return (
                        (name.includes('wheat') && b.metadata === 7) ||
                        (name.includes('carrot') && b.metadata === 7) ||
                        (name.includes('potato') && b.metadata === 7) ||
                        (name.includes('beetroot') && b.metadata === 7)
                    );
                },
                maxDistance: 20,
                count: 999
            });
            if (crops.length) {
                bot.chat(`Farming ${crops.length} crops...`);
                for (const pos of crops) {
                    const block = bot.blockAt(pos);
                    if (!block) continue;
                    bot.pathfinder.setGoal(new GoalNear(pos.x, pos.y, pos.z, 1));
                    await bot.waitForTicks(5);
                    await bot.dig(block);

                    // Try to replant from inventory
                    let seedItem = null;
                    if (block.name.includes('wheat')) seedItem = bot.inventory.items().find(i => i.name.includes('wheat_seeds'));
                    if (block.name.includes('carrot')) seedItem = bot.inventory.items().find(i => i.name.includes('carrot'));
                    if (block.name.includes('potato')) seedItem = bot.inventory.items().find(i => i.name.includes('potato'));
                    if (block.name.includes('beetroot')) seedItem = bot.inventory.items().find(i => i.name.includes('beetroot'));

                    // If no seed in inventory, check home chest
                    if (!seedItem && homeChest) {
                        const homePos = new Vec3(homeChest.x, homeChest.y, homeChest.z);
                        const chestBlock = bot.blockAt(homePos);
                        if (chestBlock && chestBlock.name.includes('chest')) {
                            try {
                                const chest = await bot.openChest(chestBlock);
                                const chestItem = chest.containerItems().find(i => i.name.includes(block.name.split('_')[0]));
                                if (chestItem) seedItem = chestItem;
                                chest.close();
                            } catch (e) { }
                        }
                    }

                    if (seedItem) {
                        await bot.equip(seedItem, 'hand');
                        const soilBlock = bot.blockAt(pos.offset(0, -1, 0));
                        if (soilBlock) await bot.placeBlock(soilBlock, Vec3(0, 1, 0));
                    }

                    if (bot.inventory.items().length > 28) await depositAllExceptTools();
                }
            }

            // 3️⃣ Strip Mine Ores
            const mineStart = bot.entity.position.offset(-5, -1, -5);
            const mineEnd = bot.entity.position.offset(5, -5, 5);
            await stripMineArea(mineStart, mineEnd, true); // ores only
            await depositAllExceptTools();

            // Wait a few ticks before repeating
            await new Promise(r => setTimeout(r, 2000));

        } catch (err) {
            bot.chat(`Auto mode error: ${err.message}`);
        }
    }
}

// -------------------
// Command toggle
// -------------------
function toggleAutoMode(enable) {
    if (enable) {
        if (autoMode) return bot.chat("Auto mode already running.");
        autoMode = true;
        bot.chat("Auto mode enabled ✅");
        autoTasks(); // start async loop
    } else {
        autoMode = false;
        bot.chat("Auto mode disabled ❌");
    }
}


// -----------------------------
// Chat bridge -> send to Python
// -----------------------------
bot.on('chat', (username, message) => {
    sendEvent({ event: 'chat', user: username, message });
});

// -----------------------------
// Command reader (from Python stdin)
// -----------------------------
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
                if (msg.args.player && defaultMove) await comeToPlayer(msg.args.player);
                break;

            case 'jump':
                bot.setControlState('jump', true);
                setTimeout(() => bot.setControlState('jump', false), 500);
                bot.chat('Jumped!');
                break;

            case 'help':
                bot.chat('Commands: !hello, !status, !time, !date, !report, !auto <on/off>, !jump, !come, !respawn, !chest, !follow <player>, !follow, !stop, !deforest, !farm, !stripmine x1 y1 z1 x2 y2 z2, !equip, !defend, !sethome, !home');
                break;

            case 'auto':
                if (msg.args.state === true) toggleAutoMode(true);
                else if (msg.args.state === false) toggleAutoMode(false);
                else toggleAutoMode(!autoMode); // toggle if no args
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

            case 'sethome':
                await setHomeAtNearbyChest();
                break;

            case 'home':
                await goHomeAndDeposit();
                break;

            case 'follow':
                if (msg.args.player) startFollowing(msg.args.player);
                break;

            case 'stop':
                stopAllIntervals();
                break;

            case 'deforest':
                await deforest(50); // default 50 block radius
                break;

            case 'farm':
                await farmCrops(20);
                break;

            case 'stripmine':
                const start = msg.args.start;
                const end = msg.args.end;
                if (start && end) {
                    await stripMineArea(
                        new Vec3(start.x, start.y, start.z),
                        new Vec3(end.x, end.y, end.z),
                        msg.args.onlyOres || false
                    );
                } else {
                    bot.chat('Usage: !stripmine x1 y1 z1 x2 y2 z2 [onlyOres]');
                }
                break;

            case 'equip':
                await equipBestArmor();
                break;

            case 'defend':
                startDefending();
                break;

            /*
                        case 'move': {
                            const dir = msg.args.direction;
                            const controls = ['forward', 'back', 'left', 'right'];
                            if (controls.includes(dir)) {
                                bot.setControlState(dir, true);
                                setTimeout(() => bot.setControlState(dir, false), 1000);
                                bot.chat(`Moved ${dir}`);
                            }
                            break;
                        }
                        
                        case 'pickup': {
                            const item = bot.nearestEntity(e => e.type === 'object' && e.objectType === 'item');
                            if (item) {
                                bot.pathfinder.setGoal(new GoalNear(item.position.x, item.position.y, item.position.z, 1));
                                bot.chat(`Going to pick up item`);
                            } else {
                                bot.chat('No items nearby.');
                            }
                            break;
                        }
                        
                        case 'chop': {
                            const block = bot.findBlock({ matching: b => b.name.includes('log'), maxDistance: 16 });
                            if (block) {
                                await bot.dig(block);
                                bot.chat('Chopped a tree!');
                            } else {
                                bot.chat('No trees nearby.');
                            }
                            break;
                        }
            */
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
