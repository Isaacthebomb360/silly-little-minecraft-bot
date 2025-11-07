const mineflayer = require('mineflayer')
const { pathfinder, Movements, goals } = require('mineflayer-pathfinder')
const readline = require('readline')
const mcDataLib = require('minecraft-data')

// Basic config
const HOST = process.env.HOST || 'localhost'
const PORT = parseInt(process.env.PORT || '25565')
const USERNAME = process.env.USERNAME || 'PythonBot'

const bot = mineflayer.createBot({ host: HOST, port: PORT, username: USERNAME })
bot.loadPlugin(pathfinder)

bot.once('spawn', () => {
    const mcData = require('minecraft-data')(bot.version)
    const defaultMove = new Movements(bot, mcData)
    bot.pathfinder.setMovements(defaultMove)
})

// Listen for JSON commands from Python
const rl = readline.createInterface({ input: process.stdin, output: process.stdout })
rl.on('line', line => {
    try {
        const msg = JSON.parse(line)
        if (msg.command === "chat") {
            bot.chat(msg.args.message)
        } else if (msg.command === "come") {
            const pos = msg.args.position
            const goal = new goals.GoalBlock(pos.x, pos.y, pos.z)
            bot.pathfinder.setGoal(goal)
        }
    } catch(e) {
        console.error("Invalid command:", e)
    }
})

// Relay chat events back to Python
bot.on('chat', (username, message) => {
    console.log(JSON.stringify({ event: 'chat', user: username, message }))
})
