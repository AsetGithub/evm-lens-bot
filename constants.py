# constants.py
# File ini berisi semua variabel konstan yang digunakan di seluruh proyek.

CHAIN_CONFIG = {
    'ethereum': {'explorer_url': 'https://etherscan.io', 'rpc_subdomain': 'eth-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'arbitrum': {'explorer_url': 'https://arbiscan.io', 'rpc_subdomain': 'arb-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'optimism': {'explorer_url': 'https://optimistic.etherscan.io', 'rpc_subdomain': 'opt-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'base': {'explorer_url': 'https://basescan.org', 'rpc_subdomain': 'base-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'zksync': {'explorer_url': 'https://explorer.zksync.io', 'rpc_subdomain': 'zksync-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'linea': {'explorer_url': 'https://lineascan.build', 'rpc_subdomain': 'linea-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'scroll': {'explorer_url': 'https://scrollscan.com', 'rpc_subdomain': 'scroll-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'blast': {'explorer_url': 'https://blastscan.io', 'rpc_subdomain': 'blast-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'zora': {'explorer_url': 'https://explorer.zora.energy', 'rpc_subdomain': 'zora-mainnet', 'coingecko_id': 'ethereum', 'symbol': 'ETH'},
    'polygon': {'explorer_url': 'https://polygonscan.com', 'rpc_subdomain': 'polygon-mainnet', 'coingecko_id': 'matic-network', 'symbol': 'MATIC'},
    'bsc': {'explorer_url': 'https://bscscan.com', 'rpc_subdomain': 'bsc-mainnet', 'coingecko_id': 'binancecoin', 'symbol': 'BNB'},
    'avalanche': {'explorer_url': 'https://snowtrace.io', 'rpc_subdomain': 'avax-mainnet', 'coingecko_id': 'avalanche-2', 'symbol': 'AVAX'},
    'fantom': {'explorer_url': 'https://ftmscan.com', 'rpc_subdomain': 'fantom-mainnet', 'coingecko_id': 'fantom', 'symbol': 'FTM'},
    'mantle': {'explorer_url': 'https://mantlescan.xyz', 'rpc_subdomain': 'mantle-mainnet', 'coingecko_id': 'mantle', 'symbol': 'MNT'},
    'cronos': {'explorer_url': 'https://cronoscan.com', 'rpc_subdomain': 'cronos-mainnet', 'coingecko_id': 'crypto-com-chain', 'symbol': 'CRO'},
    'gnosis': {'explorer_url': 'https://gnosisscan.io', 'rpc_subdomain': 'gnosis-mainnet', 'coingecko_id': 'xdai', 'symbol': 'xDAI'},
    'celo': {'explorer_url': 'https://celoscan.io', 'rpc_subdomain': 'celo-mainnet', 'coingecko_id': 'celo', 'symbol': 'CELO'},
    'astar': {'explorer_url': 'https://astar.subscan.io', 'rpc_subdomain': 'astar-mainnet', 'coingecko_id': 'astar', 'symbol': 'ASTR'},
    'metis': {'explorer_url': 'https://andromeda-explorer.metis.io', 'rpc_subdomain': 'metis-mainnet', 'coingecko_id': 'metis-token', 'symbol': 'METIS'},
    'degen': {'explorer_url': 'https://explorer.degen.tips', 'rpc_subdomain': 'degen-mainnet', 'coingecko_id': 'degen-base', 'symbol': 'DEGEN'},
    'opbnb': {'explorer_url': 'https://opbnb.bscscan.com', 'rpc_subdomain': 'opbnb-mainnet', 'coingecko_id': 'binancecoin', 'symbol': 'BNB'},
}