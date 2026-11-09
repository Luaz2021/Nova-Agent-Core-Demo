import sys, asyncio
from playwright.async_api import async_playwright
TIMES=[float(x) for x in sys.argv[1].split(',')]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        pg=await b.new_page(viewport={'width':1920,'height':1080})
        errs=[]
        pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None)
        await pg.goto('file://'+__import__('os').path.abspath('printlab_video.html'))
        await pg.wait_for_timeout(800)
        await pg.evaluate("document.getElementById('bigplay').hidden=true")
        for t in TIMES:
            await pg.evaluate(f'window.renderAt({t})')
            await pg.locator('#cv').screenshot(path=f'shot_{t:06.1f}.jpg',type='jpeg',quality=80)
        print('errors:',errs[:5])
        await b.close()
asyncio.run(main())
