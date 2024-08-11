<script setup>
import { ref, provide } from 'vue';
import Home from './components/Home.vue';
import Channel from './components/Channel.vue';
import APIKey from './components/APIKey.vue';
import { setPassword, getPassword, clearPassword, checkPassword } from './common/account';
import { ElMessageBox, ElMessage } from 'element-plus';

const currentTab = ref('home');

provide('currentTab', currentTab);

function showLoginDialog() {
    ElMessageBox.prompt('Please enter your token:', 'Enter token', {
        confirmButtonText: 'OK',
        cancelButtonText: 'Cancel',
        inputType: 'password',
        inputPattern: /\S+/,
        inputErrorMessage: 'Invalid Format'
    })
    .then(({ value }) => {
        checkPassword(value);
    })
    .catch(() => {
        ElMessage({
            type: 'info',
            message: 'Input canceled'
        });
    });
}

function switchTab(target) {
    if (getPassword() === "") {
        showLoginDialog();
        return;
    }
    currentTab.value = target;
}

function logout() {
    clearPassword();
    currentTab.value = 'home';
}
</script>

<template>
    <el-container>
        <el-header>
            <el-menu mode="horizontal" :router="true" :default-active="currentTab">
                <el-menu-item index="home" @click="switchTab('home')">
                    <img class="logo" src="./assets/logo.png" alt="logo">
                    <span>LLM API</span>
                </el-menu-item>
                <el-menu-item index="channel" @click="switchTab('channel')">Channels</el-menu-item>
                <el-menu-item index="apikey" @click="switchTab('apikey')">API Keys</el-menu-item>
                <el-menu-item index="login" class="login-item">
                    <el-button 
                        :type="getPassword() === '' ? 'primary' : 'danger'"
                        @click="getPassword() === '' ? showLoginDialog() : logout()"
                    >
                        {{ getPassword() === '' ? 'Login' : 'Logout' }}
                    </el-button>
                </el-menu-item>
            </el-menu>
        </el-header>

        <el-main>
            <Home v-if="currentTab === 'home'" />
            <Channel v-if="currentTab === 'channel'" />
            <APIKey v-if="currentTab === 'apikey'" />
        </el-main>
    </el-container>
</template>

<style>
body {
    margin: 0;
    font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
}

.el-container {
    min-height: 100vh;
}

.el-header {
    padding: 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, .12);
}

.el-menu {
    border-bottom: none;
}

.logo {
    height: 32px;
    margin-right: 10px;
    vertical-align: middle;
}

.login-item {
    float: right;
}

.el-main {
    padding: 20px;
}

@media (max-width: 768px) {
    .el-menu--horizontal > .el-menu-item {
        padding: 0 10px;
    }
    
    .logo {
        height: 24px;
    }
}
</style>