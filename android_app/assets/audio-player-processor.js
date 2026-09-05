/**
 * PCDeck Pro - Real-Time Low-Latency AudioWorklet Processor
 * Runs on the operating system dedicated high-priority audio thread.
 * Completely immune to main-thread UI stalls, screen decoding, and touch latency.
 */

class PCDeckAudioPlayerProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.RING_SIZE = 48000 * 2;
    this.bufferL = new Float32Array(this.RING_SIZE);
    this.bufferR = new Float32Array(this.RING_SIZE);
    this.writePos = 0;
    this.readPos = 0;
    this.available = 0;
    this.fracPos = 0.0;
    this.srcRate = 48000;
    this.channels = 2;
    this.isPrebuffering = true;
    this.lastSampleL = 0.0;
    this.lastSampleR = 0.0;

    this.port.onmessage = (event) => {
      const msg = event.data;
      if (!msg) return;

      if (msg.type === 'cfg') {
        this.srcRate = msg.sampleRate || 48000;
        this.channels = msg.channels || 2;
        return;
      }

      if (msg.type === 'reset') {
        this.writePos = 0;
        this.readPos = 0;
        this.available = 0;
        this.fracPos = 0.0;
        this.isPrebuffering = true;
        this.lastSampleL = 0.0;
        this.lastSampleR = 0.0;
        return;
      }

      if (msg instanceof ArrayBuffer) {
        const int16 = new Int16Array(msg);
        const ch = this.channels;
        const frames = Math.floor(int16.length / ch);
        if (frames <= 0) return;

        for (let i = 0; i < frames; i++) {
          const sL = int16[i * ch] / 32768.0;
          const sR = ch > 1 ? int16[i * ch + 1] / 32768.0 : sL;

          this.bufferL[this.writePos] = sL;
          this.bufferR[this.writePos] = sR;
          this.writePos = (this.writePos + 1) % this.RING_SIZE;
          this.available = Math.min(this.RING_SIZE, this.available + 1);
        }
      }
    };
  }

  process(inputs, outputs, parameters) {
    const output = outputs[0];
    if (!output || output.length === 0) return true;

    const outL = output[0];
    const outR = output.length > 1 ? output[1] : output[0];
    const bufLen = outL.length;

    const hwRate = typeof sampleRate !== 'undefined' ? sampleRate : 48000;
    const baseRatio = this.srcRate / hwRate;

    const prebufferThreshold = Math.round(this.srcRate * 0.065);
    if (this.isPrebuffering) {
      if (this.available < prebufferThreshold) {
        outL.fill(0);
        if (outR !== outL) outR.fill(0);
        return true;
      }
      this.isPrebuffering = false;
    }

    if (this.available <= 2) {
      this.isPrebuffering = true;
      for (let i = 0; i < bufLen; i++) {
        if (i < 32) {
          const fade = (32 - i) / 32;
          outL[i] = this.lastSampleL * fade;
          if (outR !== outL) outR[i] = this.lastSampleR * fade;
        } else {
          outL[i] = 0;
          if (outR !== outL) outR[i] = 0;
        }
      }
      this.lastSampleL = 0.0;
      this.lastSampleR = 0.0;
      return true;
    }

    const bufferedMs = (this.available / this.srcRate) * 1000;
    let rateMult = 1.0;
    if (bufferedMs > 80) {
      rateMult = 1.018;
    } else if (bufferedMs < 35) {
      rateMult = 0.982;
    }
    const effectiveRatio = baseRatio * rateMult;

    for (let i = 0; i < bufLen; i++) {
      if (this.available <= 1) {
        outL[i] = 0;
        if (outR !== outL) outR[i] = 0;
        continue;
      }

      const idx0 = this.readPos;
      const idx1 = (this.readPos + 1) % this.RING_SIZE;
      const alpha = this.fracPos;

      const sL = this.bufferL[idx0] * (1.0 - alpha) + this.bufferL[idx1] * alpha;
      const sR = this.bufferR[idx0] * (1.0 - alpha) + this.bufferR[idx1] * alpha;

      outL[i] = sL;
      if (outR !== outL) outR[i] = sR;
      this.lastSampleL = sL;
      this.lastSampleR = sR;

      this.fracPos += effectiveRatio;
      if (this.fracPos >= 1.0) {
        const step = Math.floor(this.fracPos);
        this.fracPos -= step;
        this.readPos = (this.readPos + step) % this.RING_SIZE;
        this.available = Math.max(0, this.available - step);
      }
    }
    return true;
  }
}

try {
  registerProcessor('pcdeck-audio-player-worklet', PCDeckAudioPlayerProcessor);
} catch (e) {}
