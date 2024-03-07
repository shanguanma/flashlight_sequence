# flashlight_sequence
It is modified from https://github.com/flashlight/sequence

This project mainly serves the fairseq_speechtext ASR decoder part
Avoid unnecessary errors caused by upstream updates


# The function of this  project:
- A fast, parallel CPU implementation of the Viterbi algorithm for greedy "argmax-style" decoding
- Fast implementations (CPU and CUDA) of the Wav2letter ASG loss function including the fully-connected and forced-alignment algorithms.

# How to use it ?
 You can see code 
`https://github.com/shanguanma/fairseq_speechtext/blob/main/examples/speech_recognition/w2l_decoder.py`
`https://github.com/shanguanma/fairseq_speechtext/blob/main/examples/speech_recognition/new/infer_simple.py` 

