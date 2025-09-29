import { startBrowserAgent } from "magnitude-core";
import dotenv from 'dotenv';

dotenv.config();

async function main() {
    const agent = await startBrowserAgent({
        url: 'https://docs.google.com/presentation/u/0/',
        browser: {
            cdp: "http://localhost:9222"
        },
        narrate: true,
        llm: {
            provider: 'anthropic',
            options: {
                model: 'claude-sonnet-4-5',
                apiKey: process.env.ANTHROPIC_API_KEY
            }
        },
    });

    await agent.act('Navigate to the presentation and make a presentation on the roman empire.');

    await agent.stop();
}

main();
