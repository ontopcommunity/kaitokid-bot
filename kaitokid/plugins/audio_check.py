import os
import asyncio
import librosa
import librosa.display
import numpy as np
import logging
from logging import getLogger
import mutagen
from pyrogram import filters
from pyrogram.types import Message, Audio, Document
from pyrogram.enums import ChatType
from kaitokid import app
from kaitokid.core.decorator.errors import capture_err
from kaitokid.vars import COMMAND_HANDLER
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import gc
import uuid
from typing import Optional, Union, Tuple

# --- CÁC HẰNG SỐ VÀ CẤU HÌNH ---
LOGGER = getLogger("KaitoKid")
__MODULE__ = "PhânTíchNhạc"
__HELP__ = """

<blockquote>/phantichnhac - Phân tích tệp âm thanh được gửi kèm hoặc trong tin nhắn trả lời (WAV, MP3, FLAC, OGG, AAC...) trong nhóm. Bot sẽ tải tệp, phân tích và gửi lại biểu đồ Waveform, Spectrogram cùng các thông tin như tần số mẫu, độ dài, kích thước tệp, biên độ, bitrate, dải động, trọng tâm phổ, nhịp độ, độ rõ nét, độ cân bằng âm sắc và đánh giá chất lượng âm thanh.

Lưu ý: Chỉ sử dụng trong nhóm. Tệp âm thanh phải nhỏ hơn 2GB. Chỉ một phiên phân tích được chạy tại một thời điểm.</blockquote>

"""

# Giới hạn phân tích
MAX_FILE_SIZE = 2_147_483_648  # 2 GB
MAX_ANALYSIS_DURATION_SECONDS = 300  # 5 phút

# Cấu hình Librosa
TARGET_SR = 44100  # Nâng SR mục tiêu để phân tích tần số cao chính xác hơn
FFT_WINDOW_SIZE = 2048
HOP_LENGTH = 512

# Dải tần cho phân tích cân bằng âm sắc (Hz)
BASS_CUTOFF = 250
MID_CUTOFF = 4000

MIME_TO_EXT = {
    "audio/mpeg": ".mp3", "audio/mp3": ".mp3", "audio/x-wav": ".wav", "audio/wav": ".wav",
    "audio/flac": ".flac", "audio/x-flac": ".flac", "audio/ogg": ".ogg", "audio/vorbis": ".ogg",
    "audio/x-m4a": ".m4a", "audio/mp4": ".m4a", "audio/aac": ".aac",
}

active_session_lock = asyncio.Lock()

# --- CÁC HÀM TRỢ GIÚP ---

def format_file_size(size_in_bytes: int) -> str:
    if size_in_bytes < 1024: return f"{size_in_bytes} bytes"
    if size_in_bytes < 1024 ** 2: return f"{size_in_bytes / 1024:.2f} KB"
    if size_in_bytes < 1024 ** 3: return f"{size_in_bytes / (1024 ** 2):.2f} MB"
    return f"{size_in_bytes / (1024 ** 3):.2f} GB"

def get_duration_from_file(file_path: str) -> Optional[float]:
    """Đọc thời lượng âm thanh từ tệp đã tải về bằng mutagen một cách an toàn."""
    try:
        audio_info = mutagen.File(file_path)
        if audio_info:
            return audio_info.info.length
    except Exception as e:
        LOGGER.warning(f"Không thể lấy duration bằng mutagen: {e}")
    return None

def evaluate_audio_quality(bitrate, dynamic_range, stereo_balance, tonal_balance, clarity):
    """Đánh giá chất lượng dựa trên các chỉ số đã được cải thiện."""
    quality_score, comment = 0, []
    
    # 1. Bitrate (30 điểm)
    try:
        bitrate_value = int(bitrate.replace(" kbps", "")) if isinstance(bitrate, str) else 0
        if bitrate_value >= 500: quality_score += 30; comment.append("Bitrate xuất sắc (Lossless/≥500 kbps).")
        elif bitrate_value >= 320: quality_score += 25; comment.append("Bitrate tốt (320-500 kbps).")
        elif bitrate_value >= 192: quality_score += 15; comment.append("Bitrate khá (192-320 kbps).")
        else: quality_score += 5; comment.append("Bitrate thấp (<192 kbps), có thể ảnh hưởng chất lượng.")
    except (ValueError, TypeError):
        quality_score += 5; comment.append("Không xác định được bitrate.")

    # 2. Dải động (25 điểm)
    if dynamic_range >= 14: quality_score += 25; comment.append(f"Dải động (RMS) tuyệt vời (≥14 dB), âm thanh có chiều sâu.")
    elif dynamic_range >= 10: quality_score += 15; comment.append(f"Dải động (RMS) tốt (10-14 dB).")
    else: quality_score += 5; comment.append(f"Dải động (RMS) hẹp (<10 dB), âm thanh có thể bị 'bè' hoặc thiếu sức sống.")

    # 3. Cân bằng Stereo (15 điểm)
    if 0.90 <= stereo_balance <= 1.10: quality_score += 15; comment.append(f"Cân bằng stereo hoàn hảo (L/R ~{stereo_balance:.2f}).")
    elif 0.75 <= stereo_balance <= 1.25: quality_score += 10; comment.append(f"Cân bằng stereo khá tốt (L/R ~{stereo_balance:.2f}).")
    else: quality_score += 5; comment.append(f"Cân bằng stereo lệch (L/R ~{stereo_balance:.2f}), có thể do mixing hoặc lỗi.")
    
    # 4. Cân bằng âm sắc (15 điểm)
    bass, mid, treble = tonal_balance['bass'], tonal_balance['mid'], tonal_balance['treble']
    if bass > 45 or treble > 45: quality_score += 5; comment.append("Cân bằng âm sắc chưa tối ưu (quá nhiều bass/treble).")
    else: quality_score += 15; comment.append("Cân bằng âm sắc tốt, các dải tần hài hòa.")
    
    # 5. Độ rõ nét (15 điểm)
    if clarity <= 0.05: quality_score += 15; comment.append("Độ trong trẻo cao (ZCR thấp), âm thanh mượt mà.")
    else: quality_score += 8; comment.append("Độ trong trẻo vừa phải, có thể chứa nhiều âm thanh bộ gõ hoặc nhiễu.")

    if quality_score >= 90: overall = f"Chất lượng âm thanh xuất sắc. (Điểm: {quality_score}/100)"
    elif quality_score >= 70: overall = f"Chất lượng âm thanh tốt. (Điểm: {quality_score}/100)"
    elif quality_score >= 50: overall = f"Chất lượng âm thanh trung bình. (Điểm: {quality_score}/100)"
    else: overall = f"Chất lượng âm thanh dưới mức tiêu chuẩn. (Điểm: {quality_score}/100)"

    return f"**Đánh giá chất lượng**:\n{overall}\n" + "\n".join([f"- {c}" for c in comment])

# --- HÀM PHÂN TÍCH CHÍNH ---

def analyze_audio_features(
    audio_path: str, file_size: int, original_duration: Optional[float]
) -> Tuple[Optional[str], str]:
    """
    Hàm phân tích audio chính, chạy CPU-bound.
    Sử dụng các metrics nâng cao để có kết quả chính xác hơn.
    """
    y, sr, analysis_note = None, 0, ""
    try:
        # Lấy sample rate gốc trước khi load
        try:
            original_sr = librosa.get_samplerate(audio_path)
        except Exception:
            original_sr = "Không xác định"
        
        load_duration = None
        if original_duration and original_duration > MAX_ANALYSIS_DURATION_SECONDS:
            load_duration = MAX_ANALYSIS_DURATION_SECONDS
            analysis_note = f"⚠️ **Lưu ý**: Tệp quá dài, chỉ phân tích **{int(load_duration / 60)} phút đầu**."

        # Load âm thanh ở dạng STEREO để phân tích không gian
        y, sr = librosa.load(audio_path, sr=TARGET_SR, duration=load_duration, mono=False)
        gc.collect()

        duration = librosa.get_duration(y=y, sr=sr)
        
        # Chuyển về mono để phân tích các đặc tính không liên quan đến stereo
        y_mono = librosa.to_mono(y)

        # --- TÍNH TOÁN CÁC CHỈ SỐ NÂNG CAO ---
        
        # Bitrate
        bitrate = "Không xác định"
        try:
            audio_info = mutagen.File(audio_path, easy=True)
            if audio_info and 'bitrate' in audio_info:
                bitrate = f"{audio_info['bitrate'][0] // 1000} kbps"
            elif original_duration and original_duration > 0:
                bitrate = f"{int((file_size * 8) / (original_duration * 1000))} kbps"
        except Exception:
            pass
            
        # Dải động (Dynamic Range) dựa trên RMS - Chính xác hơn
        rms = librosa.feature.rms(y=y_mono, frame_length=FFT_WINDOW_SIZE, hop_length=HOP_LENGTH)[0]
        # Thêm 1e-10 để tránh log(0)
        dynamic_range = 20 * np.log10((np.max(rms) + 1e-10) / (np.percentile(rms, 10) + 1e-10))

        # Cân bằng Stereo (Stereo Balance)
        stereo_balance = 0.0
        if y.ndim > 1 and y.shape[0] == 2:
            left_channel_rms = np.mean(librosa.feature.rms(y=y[0, :]))
            right_channel_rms = np.mean(librosa.feature.rms(y=y[1, :]))
            stereo_balance = (left_channel_rms + 1e-10) / (right_channel_rms + 1e-10)
        else: # Nếu là mono
            stereo_balance = 1.0 # Cân bằng hoàn hảo

        # Cân bằng âm sắc (Tonal Balance) theo dải tần
        stft_result = librosa.stft(y=y_mono, n_fft=FFT_WINDOW_SIZE, hop_length=HOP_LENGTH)
        freqs = librosa.fft_frequencies(sr=sr, n_fft=FFT_WINDOW_SIZE)
        power_spectrum = np.abs(stft_result)**2
        
        total_power = np.sum(power_spectrum) + 1e-10
        bass_power = np.sum(power_spectrum[freqs < BASS_CUTOFF])
        mid_power = np.sum(power_spectrum[(freqs >= BASS_CUTOFF) & (freqs < MID_CUTOFF)])
        treble_power = np.sum(power_spectrum[freqs >= MID_CUTOFF])

        tonal_balance = {
            'bass': (bass_power / total_power) * 100,
            'mid': (mid_power / total_power) * 100,
            'treble': (treble_power / total_power) * 100
        }
        
        # Thêm Zero-Crossing Rate (Clarity/Noisiness)
        zcr = np.mean(librosa.feature.zero_crossing_rate(y=y_mono))

        # Các chỉ số khác
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y_mono, sr=sr))
        
        tempo, _ = librosa.beat.beat_track(y=y_mono, sr=sr)
        tempo = round(float(tempo), 2)
        
        # Đánh giá chất lượng tổng thể
        quality_evaluation = evaluate_audio_quality(bitrate, dynamic_range, stereo_balance, tonal_balance, zcr)
        
        # --- VẼ BIỂU ĐỒ ---
        plt.figure(figsize=(12, 8))
        # Dạng sóng (chỉ vẽ kênh trái nếu là stereo)
        wave_data = y[0,:] if y.ndim > 1 else y
        plt.subplot(2, 1, 1)
        librosa.display.waveshow(wave_data, sr=sr, alpha=0.8, color='b')
        plt.title('Waveform (Dạng sóng)')
        plt.xlabel('Thời gian (s)')
        plt.ylabel('Biên độ')

        # Spectrogram
        plt.subplot(2, 1, 2)
        spectrogram_db = librosa.amplitude_to_db(np.abs(stft_result), ref=np.max)
        librosa.display.specshow(spectrogram_db, sr=sr, x_axis='time', y_axis='log', hop_length=HOP_LENGTH)
        plt.colorbar(format='%+2.0f dB')
        plt.title('Log-Frequency Spectrogram')
        plt.xlabel('Thời gian (s)')
        plt.ylabel('Tần số (Hz)')
        
        plt.figtext(0.99, 0.01, 'Phân tích bởi KaitoKid', ha='right', fontsize=10, bbox={"facecolor":"white", "alpha":0.8, "pad":5})
        plt.tight_layout()
        
        output_path = f"downloads/{uuid.uuid4()}_analysis.png"
        plt.savefig(output_path, format='png', bbox_inches='tight', dpi=100)
        plt.close('all')
        gc.collect()

        # --- TẠO KẾT QUẢ ---
        display_duration = f"{original_duration:.2f} giây" if original_duration else "Không xác định"
        info = (
            f"📊 **Kết quả phân tích**:\n"
            f"{analysis_note}\n\n"
            f"🔊 **Thông số cơ bản**:\n"
            f"  - Tần số mẫu: `{original_sr} Hz` (phân tích ở `{sr} Hz`)\n"
            f"  - Độ dài: `{display_duration}`\n"
            f"  - Kích thước: `{format_file_size(file_size)}`\n"
            f"  - Bitrate (ước tính): `{bitrate}`\n"
            f"  - Nhịp độ (Tempo): `{tempo} BPM`\n\n"
            f"🔬 **Phân tích chuyên sâu**:\n"
            f"  - Dải động (RMS): `{dynamic_range:.2f} dB`\n"
            f"  - Cân bằng Stereo (L/R): `{stereo_balance:.2f}`\n"
            f"  - Độ trong trẻo (ZCR): `{zcr:.3f}`\n"
            f"  - Trọng tâm phổ: `{spectral_centroid:.2f} Hz`\n"
            f"  - Cân bằng âm sắc: `Âm trầm {tonal_balance['bass']:.1f}%` / `Âm trung {tonal_balance['mid']:.1f}%` / `Âm cao {tonal_balance['treble']:.1f}%`\n\n"
            f"{quality_evaluation}"
        )
        return output_path, info

    except Exception as e:
        LOGGER.error(f"Lỗi khi phân tích: {e}", exc_info=True)
        return None, f"Lỗi khi phân tích âm thanh: {str(e)}"
    finally:
        del y, sr
        gc.collect()

# --- CÁC HÀM XỬ LÝ TELEGRAM ---

def get_audio_from_message(message: Message) -> Optional[Union[Audio, Document]]:
    target = message.reply_to_message or message
    if target.audio: return target.audio
    if target.document and target.document.mime_type and target.document.mime_type.startswith("audio/"): return target.document
    return None

def get_file_extension(audio_object: Union[Audio, Document]) -> str:
    if audio_object.file_name:
        _ , ext = os.path.splitext(audio_object.file_name)
        if ext: return ext.lower()
    if audio_object.mime_type in MIME_TO_EXT: return MIME_TO_EXT[audio_object.mime_type]
    return ".tmp"

@app.on_message(filters.command(["phantichnhac"], COMMAND_HANDLER))
@capture_err
async def phantichnhac_command(_, ctx: Message):
    if active_session_lock.locked():
        await ctx.reply("⚠️ Đang có một phiên phân tích chạy, vui lòng đợi!", quote=True)
        return

    async with active_session_lock:
        if ctx.chat.type == ChatType.PRIVATE:
            await ctx.reply("⚠️ Lệnh này chỉ được dùng trong nhóm!", quote=True)
            return
            
        audio_obj = get_audio_from_message(ctx)
        if not audio_obj:
            await ctx.reply("Vui lòng gửi kèm hoặc trả lời một tệp âm thanh!", quote=True)
            return

        msg = await ctx.reply("Đang chuẩn bị phân tích...", quote=True)
        file_path, output_image = None, None
        
        try:
            if audio_obj.file_size > MAX_FILE_SIZE:
                await msg.edit(f"⚠️ Tệp quá lớn! ({format_file_size(audio_obj.file_size)})")
                return

            file_ext = get_file_extension(audio_obj)
            file_path = f"downloads/{audio_obj.file_unique_id}{file_ext}"
            os.makedirs("downloads", exist_ok=True)

            await msg.edit(f"📥 Đang tải tệp ({format_file_size(audio_obj.file_size)})...")
            await app.download_media(audio_obj, file_name=file_path)

            await msg.edit("📋 Đang đọc siêu dữ liệu...")
            file_duration = get_duration_from_file(file_path)
            if not file_duration:
                 # Dự phòng nếu mutagen thất bại
                 file_duration = audio_obj.duration if hasattr(audio_obj, 'duration') else 0

            await msg.edit("🔍 Đang phân tích (quá trình này có thể mất một lúc)...")
            
            # Chạy hàm phân tích CPU-bound trong một luồng riêng
            output_image, info = await asyncio.to_thread(
                analyze_audio_features, 
                file_path, 
                audio_obj.file_size, 
                file_duration
            )

            if output_image:
                await ctx.reply_photo(
                    photo=output_image,
                    caption=info,
                    reply_to_message_id=ctx.id
                )
                await msg.delete()
            else:
                await msg.edit(info)

        except Exception as e:
            LOGGER.error(f"Lỗi trong phantichnhac_command: {e}", exc_info=True)
            await msg.edit(f"Lỗi không xác định: {str(e)}")
        finally:
            for path in [file_path, output_image]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError as e:
                        LOGGER.error(f"Không thể xóa tệp {path}: {e}")
            gc.collect()
