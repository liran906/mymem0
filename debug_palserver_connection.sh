#!/bin/bash

echo "======================================================================"
echo "PalServer连接诊断脚本"
echo "======================================================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查.env文件中的PALSERVER_BASE_URL
echo "1. 检查 .env 文件配置"
echo "----------------------------------------------------------------------"
if [ -f .env ]; then
    PALSERVER_URL=$(grep PALSERVER_BASE_URL .env | cut -d '=' -f2)
    if [ -z "$PALSERVER_URL" ]; then
        echo -e "${RED}✗ .env 文件中未设置 PALSERVER_BASE_URL${NC}"
        echo "请在 .env 文件中添加："
        echo "PALSERVER_BASE_URL=http://172.18.168.239:8099/pal"
    else
        echo -e "${GREEN}✓ .env 中配置的值: $PALSERVER_URL${NC}"
    fi
else
    echo -e "${RED}✗ .env 文件不存在${NC}"
fi
echo ""

# 2. 检查容器内环境变量
echo "2. 检查容器内实际环境变量"
echo "----------------------------------------------------------------------"
CONTAINER_ENV=$(docker exec mem0-api printenv PALSERVER_BASE_URL 2>/dev/null)
if [ $? -eq 0 ]; then
    if [ -z "$CONTAINER_ENV" ]; then
        echo -e "${RED}✗ 容器内 PALSERVER_BASE_URL 为空${NC}"
        echo "原因：.env 中可能未设置，或docker-compose.production.yaml使用了空值"
    else
        echo -e "${GREEN}✓ 容器内的值: $CONTAINER_ENV${NC}"
    fi
else
    echo -e "${RED}✗ 无法获取容器环境变量（容器可能未运行）${NC}"
fi
echo ""

# 3. 检查宿主机PalServer端口
echo "3. 检查宿主机 PalServer 端口监听"
echo "----------------------------------------------------------------------"
if netstat -tln 2>/dev/null | grep -q :8099 || ss -tln 2>/dev/null | grep -q :8099; then
    echo -e "${GREEN}✓ 宿主机正在监听 8099 端口${NC}"

    # 尝试从宿主机访问
    echo "  测试从宿主机访问..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8099/pal/child/1/summary --max-time 2 2>/dev/null)
    if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "404" ]; then
        echo -e "  ${GREEN}✓ 宿主机可以访问 PalServer (HTTP $RESPONSE)${NC}"
    else
        echo -e "  ${YELLOW}⚠ 无法从宿主机访问 PalServer (HTTP $RESPONSE)${NC}"
    fi
else
    echo -e "${RED}✗ 宿主机未监听 8099 端口${NC}"
    echo "  请检查 PalServer 是否运行："
    echo "  docker ps | grep palserver"
fi
echo ""

# 4. 检查容器能否访问宿主机
echo "4. 检查容器访问宿主机网络"
echo "----------------------------------------------------------------------"

# 获取宿主机IP
HOST_IP=$(hostname -I | awk '{print $1}')
echo "  宿主机IP: $HOST_IP"

# 从容器内测试宿主机IP
echo "  测试从容器访问宿主机IP ($HOST_IP:8099)..."
docker exec mem0-api curl -s -o /dev/null -w "HTTP %{http_code}" http://$HOST_IP:8099/pal/child/1/summary --max-time 2 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓ 容器可以访问宿主机 $HOST_IP:8099${NC}"
else
    echo -e "  ${RED}✗ 容器无法访问宿主机 $HOST_IP:8099${NC}"
    echo "  可能原因："
    echo "  1. PalServer 没有绑定到 0.0.0.0"
    echo "  2. 防火墙阻止了容器访问宿主机"
    echo "  3. Docker网络配置问题"
fi
echo ""

# 5. 检查Docker网络模式
echo "5. 检查 Docker 网络配置"
echo "----------------------------------------------------------------------"
NETWORK_MODE=$(docker inspect mem0-api --format='{{.HostConfig.NetworkMode}}' 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "  网络模式: $NETWORK_MODE"

    if [ "$NETWORK_MODE" = "host" ]; then
        echo -e "  ${GREEN}✓ 使用 host 网络，可以直接用 localhost${NC}"
        echo "  建议 PALSERVER_BASE_URL=http://localhost:8099/pal"
    else
        echo "  使用桥接网络，需要用宿主机IP"
        echo "  建议 PALSERVER_BASE_URL=http://$HOST_IP:8099/pal"
    fi
else
    echo -e "  ${RED}✗ 无法获取网络模式${NC}"
fi
echo ""

# 6. 提供解决方案
echo "======================================================================"
echo "解决方案建议"
echo "======================================================================"
echo ""

if [ -z "$CONTAINER_ENV" ]; then
    echo -e "${YELLOW}问题：容器内环境变量为空${NC}"
    echo "解决步骤："
    echo "  1. 编辑 .env 文件，添加："
    echo "     PALSERVER_BASE_URL=http://$HOST_IP:8099/pal"
    echo ""
    echo "  2. 重启服务："
    echo "     docker-compose -f docker-compose.production.yaml down"
    echo "     docker-compose -f docker-compose.production.yaml up -d"
    echo ""
elif [ "$CONTAINER_ENV" = "http://localhost:8099/pal" ]; then
    echo -e "${YELLOW}问题：容器内使用了 localhost（容器内部地址）${NC}"
    echo "解决步骤："
    echo "  1. 修改 .env 文件："
    echo "     PALSERVER_BASE_URL=http://$HOST_IP:8099/pal"
    echo ""
    echo "  2. 重启服务："
    echo "     docker-compose -f docker-compose.production.yaml down"
    echo "     docker-compose -f docker-compose.production.yaml up -d"
    echo ""
else
    echo "当前配置："
    echo "  容器内: $CONTAINER_ENV"
    echo "  宿主机IP: $HOST_IP"
    echo ""
    echo "如果仍然无法连接，尝试："
    echo "  1. 手动测试："
    echo "     docker exec mem0-api curl -v http://$HOST_IP:8099/pal/child/1/summary"
    echo ""
    echo "  2. 检查PalServer日志："
    echo "     docker logs <palserver-container-name>"
    echo ""
    echo "  3. 检查防火墙："
    echo "     sudo iptables -L | grep 8099"
fi

echo ""
echo "======================================================================"
echo "完成诊断"
echo "======================================================================"