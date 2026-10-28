package dev.ftb.mods.ftbchunks.api.event;

import dev.architectury.event.Event;

public interface ClaimedChunkEvent {
    Event<After> AFTER_CLAIM = new Event<>();

    @FunctionalInterface
    interface After {
        void after(Object source, Object claimedChunk);
    }
}
