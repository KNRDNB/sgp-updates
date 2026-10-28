package dev.architectury.event;

public interface Event<T> {
    void register(T listener);
}
