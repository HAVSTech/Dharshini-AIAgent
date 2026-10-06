# Dharshini wake-word model

Place your custom openWakeWord-compatible model here:

```
models/dharshini.tflite
```

The runtime expects 16 kHz, 16-bit mono PCM and performs wake-word detection locally on the Windows machine. No Gemini request is made while Dharshini is in wake-word standby.

## Training

The project uses openWakeWord as the local runtime. A custom model for the phrase **Dharshini** must be trained separately and copied here.

openWakeWord provides an automated custom-model training workflow. Its example configuration supports setting a target phrase and exporting a deployable model. See:

https://github.com/dscripka/openWakeWord

For a higher-quality personal wake word, include real recordings of the intended speaker/environment when evaluating the model.

The application intentionally falls back to always-listening voice mode when this model file is not present, so a missing model cannot break the main assistant.
