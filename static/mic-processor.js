/**
 * PCDeck Pro - Low-Latency AudioWorklet PCM Processor
 * Converts raw browser Float32 microphone input to Linear 16-bit Int16 PCM chunks
 * and streams them across the thread boundary without GC allocation pauses.
 */

class MicWorkletProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.isMuted = false;
    this.gain = 1.0;

    this.port.onmessage = (event) => {
      const data = event.data;
      if (data) {
        if (typeof data.isMuted === 'boolean') {
          this.isMuted = data.isMuted;
        }
        if (typeof data.gain === 'number') {
          this.gain = data.gain;
        }
      }
    };
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0] || this.isMuted) {
      return true;
    }

    const inputChannel = input[0];
    const sampleCount = inputChannel.length;
    const int16Buffer = new Int16Array(sampleCount);

    for (let i = 0; i < sampleCount; i++) {
      let sample = inputChannel[i] * this.gain;
      // Clamp to 16-bit PCM range [-32768, 32767]
      sample = Math.max(-1.0, Math.min(1.0, sample));
      int16Buffer[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    }

    // Zero-copy transfer of the ArrayBuffer to main thread
    this.port.postMessage(int16Buffer.buffer, [int16Buffer.buffer]);
    return true;
  }
}

registerProcessor('mic-worklet-processor', MicWorkletProcessor);
