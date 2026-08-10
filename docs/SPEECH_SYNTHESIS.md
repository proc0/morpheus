# Speech Synthesis

Lab notes after synthesizing audio with [Piper](https://github.com/OHF-Voice/piper1-gpl/tree/main)

Goal: voice cloning with a few voice clip examples

Following these instructions:
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/TRAINING.md

## AI Summary

## Building

After ensuring the prereqs are installed, clone the piper repo and run the '.[train]' script with python. 
Then run the cython extension script.

At this point we need to build the dev build of the repo so it compiles all the C code necessary for training.
This is where there was a missing dependency in throwing an error "from skbuild import setup
ModuleNotFoundError: No module named 'skbuild'", which requires installing scikit-build within .venv

```bash
source .venv/bin/activate
pip install scikit-build
```

We can then run

```bash
python3 setup.py build_ext --inplace
```

Note: there is already a script folder with this scrip in there so this can also be run instead:

```bash
./script/dev_build
```

## Training

At this point, gather all the reference audio. Cleaning it up, name it consistently, etc. 
Create a .csv file with the filenames and transcript of the audio as outlined in the Training readme of Piper.

With this, create a folder where the training files can be place. I created the folder inside piper since we will also need the python environment for running other scripts. In this folder we have the cache for the training, and prepared files, and it will serve as the output for some of the training files like the model config.json, and the reference checkpoint model. 

Download an existing checkpoint that serves as the base for the fine-tuning. Voice checkpoints are here (also linked from the Training readme): https://huggingface.co/rhasspy/piper-voices/tree/main

Once all the files are in one place, the audio is prepared, the .csv has the transcript and file names, I create shell script with the python command for training (also in speech_synth folder):

```bash
python3 -m piper.train fit \
  --data.voice_name "Morpheus" \
  --data.csv_path ./morpheus/transcript.csv \
  --data.audio_dir ./morpheus/audio/ \
  --model.sample_rate 22050 \
  --data.espeak_voice "en-us" \
  --data.cache_dir ./morpheus/cache/ \
  --data.config_path ./morpheus/morpheus-config.json \
  --data.batch_size 32 \
  --ckpt_path ./morpheus/mike/epoch%3D5460-val_mos%3D4.2686.ckpt \
```

At this point, I ran into issue with how Piper is set up for training (which I'm not understanding exactly what is going on, but Gemma explains and offers a solution). We get a "MisconfigurationException" inside of a long error:

```
 line 587, in _save_topk_checkpoint
raise MisconfigurationException(m)
lightning.fabric.utilities.exceptions.MisconfigurationException: `ModelCheckpoint(monitor='val_mos')` could not find the monitored key in the returned metrics
```

This has to do with what metric is being used to create a checkpoint, and for some reason val_mos is misconfigured, but I'm not clear exactly what that is or what the root cause is. After prompting Gemma, she suggests:

"Your training process is using a Checkpoint Callback. This callback is programmed to watch for a specific metric called val_mos (Validation Mean Opinion Score) so it can say, "This is the best version of the model I've seen so far; I will save this file."

However, your current training run is calculating a different set of metrics (like val_loss, val_mel, etc.), but it is not calculating val_mos. When the first epoch finishes and the system tries to save the checkpoint, it looks for val_mos, doesn't find it in the list of results, and throws a MisconfigurationException because it doesn't know how to determine if the model has improved.

This often happens when you use a pre-trained checkpoint (like the "Mike" one) that was originally trained with MOS-monitoring enabled, but your current local environment/config is set up for standard loss-monitoring."

The suggested solution is to comment out a python config for the training that is located in the piper/train folder, inside the __main__.py file:

```python
    # ModelCheckpoint(
    #     monitor="val_mos",
    #     mode="max",
    #     save_top_k=5,
    #     save_last=False,
    #     filename="epoch={epoch}-val_mos={val_mos:.4f}",
    #     auto_insert_metric_name=False,
    # ),
```

This removes val_mos as a metric for creating the checkpoint, and the training can proceed.

During training we install and run tensorboard within the python env:

```bash
cd <piper source folder>
source .venv/bin/activate
pip install tensorboard
tensorboard --logdir ./lightning_logs/
```

We point at the lightning_logs and that will allow us to look at the different metrics. The train_disc and val_mel seem to be the main metrics to look at but there is a lot of research to be done as to what each metric is doing here and what to look for. Once train_disc has decreased to 1.3 and doesn't move much, we can stop the training. There is also the audio tab from where we can listen to the different checkpoints to see how the resulting checkpoint sounds and whether to continue or not.

Once it sounds good and metrics look good we stop the training with keyboard interrupt Ctrl+C.

## Exporting checkpoint

Once the training is done, the resulting checkpoint is in the lightning_logs directory. We can then use this to export to an .onnx file. During training the model config.json file was also modified accordingly and this is needed as the final two outputs of the process.

We then run into another error when trying to export (as outlined in the Training readme of Piper):

```

The following call raised this error:
File "/home/gmork/sources/piper1-gpl/src/piper/train/vits/transforms.py", line 174, in rational_quadratic_spline
assert (discriminant >= 0).all(), discriminant

```

An assertion is hit in the transform.py file inside piper/train folder. Gemma explains this is not needed for exporting and can be commented out, which fixes the issue. Here is an excerpt of that explanation:

"What's happening: When you export a model to ONNX, PyTorch doesn't just save the weights; it "traces" the mathematical graph of the model by passing dummy data through it. During this trace, the exporter encountered a line of code in Piper's VITS implementation (the rational_quadratic_spline function) that contains a Python assert statement:

```python
assert (discriminant >= 0).all(), discriminant
```

In older versions of PyTorch, these assertions were simply ignored during export. However, the new PyTorch exporter tries to be "symbolically correct." It sees an assertion that depends on the value of the data (the discriminant) and says: "I cannot guarantee that this expression will always be true for every possible input in the future, therefore I cannot safely export this graph."

Basically, a safety check meant for training is now acting as a blockade for exporting."

#### In other words, the new PyTorch is more strict, and this assertion was good for training but now needs to be commented out for exporting

And that's not all the issues with versions. Commenting that assertion will fix the export, but the export will not work properly. We get this message at the end of the export:

```
/home/gmork/sources/piper1-gpl/.venv/lib/python3.11/site-packages/torch/onnx/_internal/exporter/_compat.py:180: UserWarning: # ONNX model has different number of inputs than the flatten dynamic_shapes. The dynamic axes will not be renamed. onnx_program._rename_dynamic_axes(dynamic_shapes)INFO:__main__:Exported model to morpheus/morpheus-medium.onnx
```

And then you get 2 files instead of 1: the .onnx and a .data file. When this exports properly, it should only yield the .onnx file.

After consulting with Gemini on this one, with the explanation:

"This means your modern PyTorch version is using its default TorchDynamo exporter backend. Because the Piper codebase expects the traditional export framework, PyTorch gets confused by the structure of the input arguments, drops your dynamic_axes definitions on the floor, and bakes a frozen text sequence length (like 15) into the model. This is exactly what caused your original Where node broadcasting crash."

And the solution is to add the following argument to the torch export command:

```python
torch.onnx.export(
    model=model_g,            # Your VITS model generator
    args=dummy_input,         # The tracing dummy input tensors
    f=output_path,
    dynamo=False,             # <--- ADD THIS LINE TO FIX THE WARNING
    verbose=False,
    opset_version=OPSET_VERSION,
    input_names=["input", "input_lengths", "scales", "sid"],
    output_names=["output"],
    dynamic_axes={
        "input": {0: "batch_size", 1: "phonemes"},
        "input_lengths": {0: "batch_size"},
        "output": {0: "batch_size", 2: "time"},
    }
)
```

And so adding dynamo=False, fixes the export command. We then get a properly export .onnx file, and make sure that the .onnx, and the .json are named properly like this:

<model-name>.onnx
<model-name>.onnx.json

## Final notes

Make sure the .onnx and config.json are named properly and in the same folder. We can then load this in a python script and generate wave files. We can follow these readme for the basic setup:
https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md

