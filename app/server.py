from starlette.applications import Starlette
from starlette.responses import HTMLResponse, JSONResponse
from starlette.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import uvicorn, aiohttp, asyncio
from io import BytesIO

from fastai import *
from fastai.vision import *

# model_file_url = 'https://www.dropbox.com/s/y4kl2gv1akv7y4i/stage-2.pth?raw=1'
# monos-stage-2-clean.pth
# model_file_url = 'https://drive.google.com/uc?export=download&id=1AAeFh0LooMyOnB0jQUk8ujuz5drl7llE'
# monos-costarica.pkl
model_file_url = 'https://drive.google.com/uc?export=download&id=1QAVK-k2pRpjwkbH6wAWAJH7BG3ev44kI'
model_file_name = 'monos-costarica.pkl'
classes = ['araña', 'ardilla', 'aullador', 'capuchino']
path = Path(__file__).parent

app = Starlette()
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_headers=['X-Requested-With', 'Content-Type'])
app.mount('/static', StaticFiles(directory='app/static'))

async def download_file(url, dest):
    if dest.exists(): return
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.read()
            with open(dest, 'wb') as f: f.write(data)

async def setup_learner():
    # Modifications thanks to Jinu Daniel from fastai (single_from_classes is deprecated)
    # -----------------------------------------------------------------------------------
    # 
    # await download_file(model_file_url, path/'models'/f'{model_file_name}.pth')
    # data_bunch = ImageDataBunch.single_from_classes(path, classes,
    #     ds_tfms=get_transforms(), size=224).normalize(imagenet_stats)
    # learn = create_cnn(data_bunch, models.resnet34, pretrained=False)
    # learn.load(model_file_name)
    # return learn
    
    await download_file(model_file_url, path/model_file_name)
    try:
        learn = load_learner(path, export_file_name)
        return learn
    except RuntimeError as e:
        if len(e.args) > 0 and 'CPU-only machine' in e.args[0]:
            print(e)
            message = "\n\nThis model was trained with an old version of fastai and will not work in a CPU environment.\n\nPlease update the fastai library in your training environment and export your model again.\n\nSee instructions for 'Returning to work' at https://course.fast.ai."
            raise RuntimeError(message)
        else:
            raise

loop = asyncio.get_event_loop()
tasks = [asyncio.ensure_future(setup_learner())]
learn = loop.run_until_complete(asyncio.gather(*tasks))[0]
loop.close()

@app.route('/')
def index(request):
    html = path/'view'/'index.html'
    return HTMLResponse(html.open().read())

@app.route('/analyze', methods=['POST'])
async def analyze(request):
    data = await request.form()
    img_bytes = await (data['file'].read())
    img = open_image(BytesIO(img_bytes))
    return JSONResponse({'result': learn.predict(img)[0]})

if __name__ == '__main__':
    if 'serve' in sys.argv: uvicorn.run(app, host='0.0.0.0', port=8080)

