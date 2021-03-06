
from populus import Project
from populus.utils.wait import wait_for_transaction_receipt
from web3 import Web3
from web3.utils.compat import (
    Timeout,
)


def check_successful_tx(web3: Web3, txid: str, timeout=180) -> dict:
    """See if transaction went through (Solidity code did not throw).
    :return: Transaction receipt
    """
    receipt = wait_for_transaction_receipt(web3, txid, timeout=timeout)
    txinfo = web3.eth.getTransaction(txid)
    assert txinfo["gas"] != receipt["gasUsed"]
    print("gas used: ", receipt["gasUsed"])
    return receipt


def wait(transfer_filter):
    with Timeout(30) as timeout:
        while not transfer_filter.get(False):
            timeout.sleep(2)


def deploy(contract_name, chain, *args):
    contract = chain.provider.get_contract_factory(contract_name)
    txhash = contract.deploy(args=args)
    receipt = check_successful_tx(chain.web3, txhash)
    id_address = receipt["contractAddress"]
    print(contract_name, "contract address is", id_address)
    return contract(id_address)
    
    
def deploy_network(chain, currency_network_factory, name, symbol, decimals):
    web3 = chain.web3
    transfer_filter = currency_network_factory.on("CurrencyNetworkCreated")
    txid = currency_network_factory.transact({"from": web3.eth.accounts[0]}).CreateCurrencyNetwork(name, symbol, web3.eth.accounts[0], 1000, 100, 25, 100);
    receipt = check_successful_tx(web3, txid)
    wait(transfer_filter)
    log_entries = transfer_filter.get()
    addr_trustlines = log_entries[0]['args']['_currencyNetworkContract']
    print("Real CurrencyNetwork contract address is", addr_trustlines)

    resolver = deploy("Resolver", chain, addr_trustlines)
    receipt = check_successful_tx(web3, txid)
    transfer_filter = resolver.on("FallbackChanged")
    proxy = deploy("EtherRouter", chain, resolver.address)
    proxied_trustlines = chain.provider.get_contract_factory("CurrencyNetwork")(proxy.address)
    txid = proxied_trustlines.transact({"from": web3.eth.accounts[0]}).init(name, symbol, decimals, 1000, 100, 25, 100)
    receipt = check_successful_tx(web3, txid)
    txid = resolver.transact({"from": web3.eth.accounts[0]}).registerLengthFunction("getUsers()", "getUsersReturnSize()", addr_trustlines);
    receipt = check_successful_tx(web3, txid)
    txid = resolver.transact({"from": web3.eth.accounts[0]}).registerLengthFunction("getFriends(address)", "getFriendsReturnSize(address)", addr_trustlines);
    receipt = check_successful_tx(web3, txid)
    txid = resolver.transact({"from": web3.eth.accounts[0]}).registerLengthFunction("trustline(address,address)", "trustlineLen(address,address)", addr_trustlines);
    receipt = check_successful_tx(web3, txid)
    txid = resolver.transact({"from": web3.eth.accounts[0]}).registerLengthFunction("getAccountExt(address,address)", "getAccountExtLen()", addr_trustlines);
    receipt = check_successful_tx(web3, txid)
    txid = resolver.transact({"from": web3.eth.accounts[0]}).registerLengthFunction("name()", "nameLen()", addr_trustlines);
    receipt = check_successful_tx(web3, txid)
    txid = resolver.transact({"from": web3.eth.accounts[0]}).registerLengthFunction("symbol()", "symbolLen()", addr_trustlines);
    receipt = check_successful_tx(web3, txid)

    print("\n\naddress for accessing CurrencyNetwork through Proxy: ", proxied_trustlines.address, '\n\n')
    return proxied_trustlines.address


def main():
    project = Project('populus.json')
    chain_name = "dockerrpc"
    print("Make sure {} chain is running, you can connect to it, or you'll get timeout".format(chain_name))

    with project.get_chain(chain_name) as chain:
        web3 = chain.web3

    print("Web3 provider is", web3.currentProvider)
    registry = deploy("Registry", chain)
    currencyNetworkFactory = deploy("CurrencyNetworkFactory", chain, registry.address)
    
    networks = [("Euro", "EUR", 2), ("US Dollar", "USD", 2), ("Testcoin", "T", 6)]
    
    network_addresses = [deploy_network(chain, currencyNetworkFactory, name, symbol, decimals) for (name, symbol, decimals) in networks]
    
    with open("networks", 'w') as file_handler:
        for network_address in network_addresses:
            file_handler.write("{}\n".format(network_address))
    
    


if __name__ == "__main__":
    main()
