import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "ComfyUI.GeminiAudioRecorder",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "Gemini Audio Recorder") {
            const onNodeCreated = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function() {
                const r = onNodeCreated ? onNodeCreated.apply(this, arguments) : undefined;

                this.isRecording = false;
                this.recordingTimeout = null;

                const triggerWidget = this.widgets.find(w => w.name === "trigger");
                if (triggerWidget) {
                    triggerWidget.type = "hidden";
                    triggerWidget.hidden = true;
                    triggerWidget.value = 0;
                    triggerWidget.computeSize = function() { return [0, 0]; };
                }

                const widgetH = LiteGraph.NODE_WIDGET_HEIGHT || 20;
                const widgetGap = 4;
                const headerH = 30;
                const visibleWidgets = this.widgets.filter(w => !w.hidden);
                const widgetsBottom = headerH + visibleWidgets.length * (widgetH + widgetGap);
                const buttonH = 32;
                const minHeight = widgetsBottom + buttonH + 16;

                this.setSize([280, minHeight]);
                this.minSize = [220, minHeight];

                return r;
            };

            nodeType.prototype.onDrawForeground = function(ctx) {
                const [w, h] = this.size;
                const margin = 10;
                const buttonHeight = 32;

                const widgetH = LiteGraph.NODE_WIDGET_HEIGHT || 20;
                const widgetGap = 4;
                const headerH = 30;
                const visibleWidgets = this.widgets.filter(w => !w.hidden);
                const widgetsBottom = headerH + visibleWidgets.length * (widgetH + widgetGap);
                const buttonY = widgetsBottom + 8;

                if (buttonY + buttonHeight > h - 4) return;

                this.buttonRect = [margin, buttonY, w - margin * 2, buttonHeight];

                const [x, y, bw, bh] = this.buttonRect;

                ctx.fillStyle = this.isRecording ? "#e53935" : "#2a2a2a";
                ctx.strokeStyle = this.isRecording ? "#ff8a80" : "#666";
                ctx.lineWidth = 1;

                ctx.beginPath();
                if (ctx.roundRect) {
                    ctx.roundRect(x, y, bw, bh, 6);
                } else {
                    ctx.rect(x, y, bw, bh);
                }
                ctx.fill();
                ctx.stroke();

                ctx.fillStyle = "#fff";
                ctx.font = "bold 13px Arial, sans-serif";
                ctx.textAlign = "center";
                ctx.textBaseline = "middle";
                ctx.fillText(
                    this.isRecording ? "⏹ Recording..." : "🎤 Start Recording",
                    x + bw / 2,
                    y + bh / 2
                );
            };

            nodeType.prototype.onMouseDown = function(event, local_pos) {
                if (!this.buttonRect) return false;

                const [x, y, bw, bh] = this.buttonRect;
                if (local_pos[0] >= x && local_pos[0] <= x + bw &&
                    local_pos[1] >= y && local_pos[1] <= y + bh) {

                    if (!this.isRecording) {
                        this.isRecording = true;

                        if (this.recordingTimeout) {
                            clearTimeout(this.recordingTimeout);
                        }

                        this.recordingTimeout = setTimeout(() => {
                            this.isRecording = false;
                            app.graph.setDirtyCanvas(true);
                        }, 10000);

                        const triggerWidget = this.widgets.find(w => w.name === "trigger");
                        if (triggerWidget) {
                            triggerWidget.value = (triggerWidget.value || 0) + 1;
                        }

                        app.queuePrompt();
                    }
                    return true;
                }
                return false;
            };
        }
    }
});
