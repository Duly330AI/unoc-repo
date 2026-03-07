<template>
    <transition name="fade">
        <div v-if="s.visible" class="overlay" role="alert" aria-busy="true">
            <div class="box">
                <div class="spinner" aria-hidden="true"></div>
                <div v-if="s.message" class="msg">{{ s.message }}</div>
            </div>
        </div>
    </transition>
</template>

<script setup lang="ts">
import { useSpinnerStore } from '../../stores/spinnerStore'
const s = useSpinnerStore()
</script>

<style scoped>
.overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, .45);
    display: grid;
    place-items: center;
    z-index: 5000;
}

.box {
    background: rgba(20, 20, 20, .9);
    color: #fff;
    padding: 1rem 1.25rem;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: .6rem;
    border: 1px solid #333;
}

.spinner {
    width: 28px;
    height: 28px;
    border: 3px solid rgba(255, 255, 255, .35);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin .9s linear infinite;
}

.msg {
    font-size: .8rem;
    opacity: .9;
}

@keyframes spin {
    to {
        transform: rotate(360deg)
    }
}

.fade-enter-active,
.fade-leave-active {
    transition: opacity .15s ease
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0
}
</style>
