<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import axios from 'axios';
import { ElNotification, ElMessageBox } from 'element-plus';
import { Delete, Refresh, DocumentAdd, Timer, Edit, Search, Download } from '@element-plus/icons-vue';

const channelList = ref([]);
const loading = ref(false);
const scheduling = ref(false);
const searchQuery = ref('');
const selectedChannels = ref([]);
const sortBy = ref('id');
const sortOrder = ref('asc');

const detailsDialogVisible = ref(false);
const showingChannelIndex = ref(-1);
const showingChannelData = reactive({
    details: {
        id: "0",
        name: "",
        adapter: {
            type: "Deepinfra/Deepinfra-API",
            config: "{}"
        },
        model_mapping: "{}",
        enabled: true,
        latency: -1
    }
});

const usableAdapterList = ref([]);
const usableAdapterMap = ref({});

const filteredChannels = computed(() => {
    return channelList.value
        .filter(channel => 
            channel.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
            channel.adapter.toLowerCase().includes(searchQuery.value.toLowerCase())
        )
        .sort((a, b) => {
            const modifier = sortOrder.value === 'asc' ? 1 : -1;
            if (a[sortBy.value] < b[sortBy.value]) return -1 * modifier;
            if (a[sortBy.value] > b[sortBy.value]) return 1 * modifier;
            return 0;
        });
});

function refreshChannelList() {
    loading.value = true;
    axios.get('/api/channel/list')
        .then(res => {
            loading.value = false;
            if (res.data.code != 0) {
                ElNotification({
                    message: 'Failed: ' + res.data.message,
                    type: 'error'
                });
                return;
            }
            channelList.value = res.data.data.map(channel => ({...channel, loading: false}));
            ElNotification({
                message: 'Successfully refreshed channel list.',
                type: 'success',
                duration: 1800
            });
        })
        .catch(err => {
            loading.value = false;
            console.error(err);
            ElNotification({
                message: 'Failed to refresh channel list.',
                type: 'error'
            });
        });
}

function deleteChannelConfirmed(channel_id) {
    ElMessageBox.confirm(
        'Are you sure you want to delete this channel?',
        'Warning',
        {
            confirmButtonText: 'OK',
            cancelButtonText: 'Cancel',
            type: 'warning',
        }
    )
    .then(() => {
        axios.delete('/api/channel/delete/' + channel_id)
            .then(res => {
                if (res.data.code == 0) {
                    ElNotification({
                        message: 'Successfully deleted channel.',
                        type: 'success'
                    });
                    refreshChannelList();
                } else {
                    ElNotification({
                        message: 'Failed: ' + res.data.message,
                        type: 'error'
                    });
                }
            })
            .catch(err => {
                console.error(err);
                ElNotification({
                    message: 'Failed to delete channel.',
                    type: 'error'
                });
            });
    })
    .catch(() => {
        ElNotification({
            type: 'info',
            message: 'Delete canceled'
        });
    });
}

function testChannelLatency(channel_id) {
    const channel = channelList.value.find(c => c.id === channel_id);
    if (channel) {
        channel.loading = true;
        axios.post('/api/channel/test/' + channel_id)
            .then(res => {
                if (res.data.code == 0) {
                    channel.loading = false;
                    channel.latency = parseFloat(res.data.data.latency).toFixed(2);
                } else {
                    ElNotification({
                        message: 'Failed: ' + res.data.message + " Channel: " + channel_id,
                        type: 'error'
                    });
                    channel.loading = false;
                    channel.latency = -1;
                }
            })
            .catch(err => {
                console.error(err);
                ElNotification({
                    message: 'Failed to test channel.',
                    type: 'error'
                });
                channel.loading = false;
                channel.latency = -1;
            });
    }
}

function testAllChannelLatency() {
    scheduling.value = true;
    const promises = channelList.value.map((channel, index) => 
        new Promise(resolve => {
            setTimeout(() => {
                testChannelLatency(channel.id);
                resolve();
            }, index * 750);
        })
    );

    Promise.all(promises).then(() => {
        scheduling.value = false;
    });
}

function toggleChannelStatus(channel) {
    const action = channel.enabled ? 'disable' : 'enable';
    axios.post(`/api/channel/${action}/${channel.id}`)
        .then(res => {
            if (res.data.code == 0) {
                ElNotification({
                    message: `Successfully ${action}d channel.`,
                    type: 'success'
                });
                channel.enabled = !channel.enabled;
            } else {
                ElNotification({
                    message: 'Failed: ' + res.data.message,
                    type: 'error'
                });
            }
        })
        .catch(err => {
            console.error(err);
            ElNotification({
                message: `Failed to ${action} channel.`,
                type: 'error'
            });
        });
}

function deleteSelectedChannels() {
    if (selectedChannels.value.length === 0) {
        ElNotification({
            message: 'No channels selected.',
            type: 'warning'
        });
        return;
    }

    ElMessageBox.confirm(
        `Are you sure you want to delete ${selectedChannels.value.length} selected channels?`,
        'Warning',
        {
            confirmButtonText: 'OK',
            cancelButtonText: 'Cancel',
            type: 'warning',
        }
    )
    .then(() => {
        const deletePromises = selectedChannels.value.map(channelId => 
            axios.delete('/api/channel/delete/' + channelId)
        );

        Promise.all(deletePromises)
            .then(() => {
                ElNotification({
                    message: 'Successfully deleted selected channels.',
                    type: 'success'
                });
                refreshChannelList();
                selectedChannels.value = [];
            })
            .catch(err => {
                console.error(err);
                ElNotification({
                    message: 'Failed to delete some channels.',
                    type: 'error'
                });
            });
    })
    .catch(() => {
        ElNotification({
            type: 'info',
            message: 'Delete canceled'
        });
    });
}

function exportChannelData() {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(channelList.value));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "channel_data.json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}

function showCreateChannelDialog() {
    showingChannelIndex.value = -1;
    showingChannelData.details = {
        id: "0",
        name: "",
        adapter: {
            type: "Deepinfra/Deepinfra-API",
            config: "{}"
        },
        model_mapping: "{}",
        enabled: true,
        latency: -1
    };
    detailsDialogVisible.value = true;
}

function showDetails(channel_id) {
    const channelIndex = channelList.value.findIndex(c => c.id === channel_id);
    if (channelIndex !== -1) {
        axios.get('/api/channel/details/' + channel_id)
            .then(res => {
                showingChannelData.details = res.data.data;
                showingChannelIndex.value = channelIndex;
                detailsDialogVisible.value = true;

                showingChannelData.details.adapter.config = JSON.stringify(showingChannelData.details.adapter.config, null, 4);
                showingChannelData.details.model_mapping = JSON.stringify(showingChannelData.details.model_mapping, null, 4);
            })
            .catch(err => {
                console.error(err);
                ElNotification({
                    message: 'Failed to get channel details.',
                    type: 'error'
                });
            });
    }
}

function validateChannel() {
    if (showingChannelData.details.model_mapping === "") {
        showingChannelData.details.model_mapping = "{}";
    }

    if (showingChannelData.details.adapter.type === "") {
        ElNotification({
            message: 'Please select an adapter.',
            type: 'error'
        });
        return false;
    }

    if (showingChannelData.details.adapter.config === "") {
        showingChannelData.details.adapter.config = "{}";
    }

    if (showingChannelData.details.name === "") {
        ElNotification({
            message: 'Channel name is required.',
            type: 'error'
        });
        return false;
    }

    try {
        JSON.parse(showingChannelData.details.model_mapping);
    } catch (e) {
        ElNotification({
            message: 'Model mapping is not a valid JSON.',
            type: 'error'
        });
        return false;
    }

    try {
        JSON.parse(showingChannelData.details.adapter.config);
    } catch (e) {
        ElNotification({
            message: 'Adapter config is not a valid JSON.',
            type: 'error'
        });
        return false;
    }

    return true;
}

function applyChannelDetails() {
    if (!validateChannel()) {
        return;
    }

    const channelData = {
        ...showingChannelData.details,
        adapter: {
            ...showingChannelData.details.adapter,
            config: JSON.parse(showingChannelData.details.adapter.config)
        },
        model_mapping: JSON.parse(showingChannelData.details.model_mapping)
    };

    const isNewChannel = showingChannelIndex.value === -1;
    const apiCall = isNewChannel
        ? axios.post('/api/channel/create', channelData)
        : axios.put('/api/channel/update/' + channelData.id, channelData);

    apiCall
        .then(res => {
            if (res.data.code === 0) {
                ElNotification({
                    message: `Successfully ${isNewChannel ? 'created' : 'updated'} channel.`,
                    type: 'success'
                });
                detailsDialogVisible.value = false;
                refreshChannelList();
            } else {
                ElNotification({
                    message: 'Failed: ' + res.data.message,
                    type: 'error'
                });
            }
        })
        .catch(err => {
            console.error(err);
            ElNotification({
                message: `Failed to ${isNewChannel ? 'create' : 'update'} channel.`,
                type: 'error'
            });
        })
        .finally(() => {
            showingChannelData.details.model_mapping = JSON.stringify(JSON.parse(showingChannelData.details.model_mapping), null, 4);
            showingChannelData.details.adapter.config = JSON.stringify(JSON.parse(showingChannelData.details.adapter.config), null, 4);
        });
}

onMounted(() => {
    refreshChannelList();
    axios.get('/api/adapter/list')
        .then(res => {
            usableAdapterList.value = res.data.data;
            usableAdapterMap.value = Object.fromEntries(
                usableAdapterList.value.map(adapter => [adapter.name, adapter])
            );
        })
        .catch(err => {
            console.error(err);
            ElNotification({
                message: 'Failed to get usable adapter list.',
                type: 'error'
            });
        });
});
</script>

<template>
    <div class="channel-manager">
        <el-card class="toolbar">
            <el-row :gutter="20">
                <el-col :xs="24" :sm="8" :md="6" :lg="4" :xl="4">
                    <el-input
                        v-model="searchQuery"
                        placeholder="Search channels"
                        prefix-icon="Search"
                    />
                </el-col>
                <el-col :xs="24" :sm="16" :md="18" :lg="20" :xl="20">
                    <el-button-group>
                        <el-button type="primary" @click="showCreateChannelDialog" :icon="DocumentAdd">
                            Add Channel
                        </el-button>
                        <el-button type="success" @click="refreshChannelList" :icon="Refresh" :loading="loading">
                            Refresh
                        </el-button>
                        <el-button type="warning" @click="testAllChannelLatency" :icon="Timer" :loading="scheduling">
                            Test All
                        </el-button>
                        <el-button type="danger" @click="deleteSelectedChannels" :icon="Delete" :disabled="selectedChannels.length === 0">
                            Delete Selected
                        </el-button>
                        <el-button type="info" @click="exportChannelData" :icon="Download">
                            Export Data
                        </el-button>
                    </el-button-group>
                </el-col>
            </el-row>
        </el-card>

        <el-table
            :data="filteredChannels"
            style="width: 100%"
            @selection-change="selectedChannels = $event.map(item => item.id)"
            v-loading="loading"
        >
            <el-table-column type="selection" width="55" />
            <el-table-column prop="id" label="ID" width="80" sortable />
            <el-table-column prop="name" label="Name" sortable />
            <el-table-column prop="adapter" label="Adapter" sortable>
                <template #default="scope">
                    <el-tag :type="scope.row.adapter === 'Deepinfra/Deepinfra-API' ? 'primary' : 'success'">
                        {{ scope.row.adapter }}
                    </el-tag>
                </template>
            </el-table-column>
            <el-table-column prop="latency" label="Latency" width="120" sortable>
                <template #default="scope">
                    <el-button 
                        @click="testChannelLatency(scope.row.id)"
                        :loading="scope.row.loading"
                        :type="scope.row.latency > 0 ? 'success' : 'info'"
                        size="small"
                    >
                        {{ scope.row.latency >= 0 ? scope.row.latency + 's' : 'N/A' }}
                    </el-button>
                </template>
            </el-table-column>
            <el-table-column label="Operations" width="300">
                <template #default="scope">
                    <el-button-group>
                        <el-button 
                            :type="scope.row.enabled ? 'danger' : 'success'"
                            @click="toggleChannelStatus(scope.row)"
                            size="small"
                        >
                            {{ scope.row.enabled ? 'Disable' : 'Enable' }}
                        </el-button>
                        <el-button 
                            type="primary"
                            @click="showDetails(scope.row.id)"
                            :icon="Edit"
                            size="small"
                        >
                            Edit
                        </el-button>
                        <el-button 
                            type="danger"
                            @click="deleteChannelConfirmed(scope.row.id)"
                            :icon="Delete"
                            size="small"
                        />
                    </el-button-group>
                </template>
            </el-table-column>
        </el-table>

        <el-dialog 
            v-model="detailsDialogVisible"
            :title="showingChannelIndex >= 0 ? 'Edit Channel' : 'New Channel'"
            width="50%"
        >
            <el-form :model="showingChannelData.details" label-width="120px">
                <el-form-item label="Name">
                    <el-input v-model="showingChannelData.details.name" />
                </el-form-item>
                <el-form-item label="Adapter">
                    <el-select v-model="showingChannelData.details.adapter.type">
                        <el-option 
                            v-for="adapter in usableAdapterList" 
                            :key="adapter.name" 
                            :label="adapter.name" 
                            :value="adapter.name" 
                        />
                    </el-select>
                </el-form-item>
                <el-form-item label="Config">
                    <el-input 
                        v-model="showingChannelData.details.adapter.config" 
                        type="textarea" 
                        :rows="5"
                    />
                </el-form-item>
                <el-form-item label="Model Mapping">
                    <el-input 
                        v-model="showingChannelData.details.model_mapping" 
                        type="textarea" 
                        :rows="5"
                    />
                </el-form-item>
            </el-form>
            <template #footer>
                <span class="dialog-footer">
                    <el-button @click="detailsDialogVisible = false">Cancel</el-button>
                    <el-button type="primary" @click="applyChannelDetails">
                        {{ showingChannelIndex >= 0 ? 'Update' : 'Create' }}
                    </el-button>
                </span>
            </template>
        </el-dialog>
    </div>
</template>

<style scoped>
.channel-manager {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.toolbar {
    margin-bottom: 20px;
}

.el-button-group {
    margin-top: 10px;
}

@media (max-width: 768px) {
    .el-button-group {
        display: flex;
        flex-direction: column;
    }

    .el-button-group .el-button {
        margin-left: 0 !important;
        margin-top: 10px;
    }
}

.el-table {
    margin-top: 20px;
}
</style>