#!/bin/env bash

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
  # --trainer.callbacks.ModelCheckpoint.monitor=val_loss
