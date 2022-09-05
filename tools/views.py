'''View File for Cardano Wallet Calculator functionality
of grander Cardano Apps Django Web application. '''

from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from blockfrost import ApiError, ApiUrls, BlockFrostApi
from django.shortcuts import render

import json

#BlockFrost API which allows for querying the Cardano blockchain
api = BlockFrostApi(
    project_id='mainnetJZdBd2lCOXfHSI9ENhubJYAZ5ThYpXao',
    base_url=ApiUrls.mainnet.value,
)

#Official Ada Handle policy ID
HANDLE_POLICY_ID =  "f0ff48bbb7bbe9d59a40f1ce90e9e9d0ff5002ec48f232b49ca0fb9a"
#Rarities and prices of Ada Handles ( Legendary 1, Ultra Rare 2, Rare 3, Common 4-7, Basic 8-15 )
HANDLE_RARITIES = { "Legendary": 995, "Ultra Rare": 445, "Rare": 445, "Common": 80, "Basic": 15 }

CNFTJUNGLE_API_URL = "https://api.cnftjungle.app/assets/asset-info/"
MINSWAP_API_URL = "https://api-mainnet-prod.minswap.org/coinmarketcap/v2/pairs"
IPFS_API_URL = "https://ipfs.io/ipfs/"

def validate_address( input_address ):
    '''Function for validating the user input address. Input not matching any
    known address patterns will return an empty string. Input matching a known
    pattern but unaccessible by the Blockfrost API will also return an empty string'''

    try:
        if input_address.startswith( "addr1" ) :
            address = api.address( input_address, return_type='json' )
            return address["stake_address"]

        if input_address.startswith( "stake1" ) :
            address = api.accounts( input_address, return_type='json' )
            return address["stake_address"]

        if input_address.startswith( "$" ) :
            handle = input_address[1:]

            handle_encoded = handle.encode( 'utf-8' )
            handle_name = handle_encoded.hex()
            handle_address = api.asset_addresses( HANDLE_POLICY_ID + handle_name, return_type='json' )[0]["address"]
            address = api.address( handle_address, return_type='json' )
            return address["stake_address"]

    except ApiError:
        return ""

    return ""

def get_ada_value( valid_stake_address ):
    '''Function for geting amount of Ada in the wallet of a given valid address'''
    ada_value = 0

    #If validStakeAddress is empty, it was invalidated by validateAddress function.
    if valid_stake_address == "" :
        return ada_value

    ada_value = float( api.accounts( valid_stake_address, return_type='json' )[ "controlled_amount" ] ) / 1000000
    return ada_value

def get_api_rewards_data( valid_stake_address ):
    '''Function for geting amount of Rewards and Reward
    info in the wallet of a given valid address'''
    rewards_dict = {}

    if valid_stake_address == "" :
        return rewards_dict

    api_rewards_data = api.accounts( valid_stake_address, return_type='json' )

    total_rewards = float( api_rewards_data[ "rewards_sum" ] ) / 1000000
    total_withdrawals = float( api_rewards_data[ "rewards_sum" ] ) / 1000000
    total_withdrawable = float( api_rewards_data[ "rewards_sum" ] ) / 1000000

    rewards_dict[ "total_rewards" ] = total_rewards
    rewards_dict[ "total_withdrawals" ] = total_withdrawals
    rewards_dict[ "total_withdrawable" ] = total_withdrawable

    pool_id = api_rewards_data[ "pool_id" ]

    pool_ticker = api.pool_metadata( pool_id, return_type='json' )[ "ticker" ]
    pool_name = api.pool_metadata( pool_id, return_type='json' )[ "name" ]
    pool_homepage = api.pool_metadata( pool_id, return_type='json' )[ "homepage" ]

    rewards_dict[ "pool_ticker" ] = pool_ticker
    rewards_dict[ "pool_name" ] = pool_name
    rewards_dict[ "pool_homepage" ] = pool_homepage

    rewards_dict_list_month = api.account_rewards( valid_stake_address, order='desc', return_type='json' )
    rewards_list_month = list(rewards_dict_list_month)[0:6]

    rewards_month = 0

    for reward in rewards_list_month:
        rewards_month = rewards_month + ( float( reward[ 'amount' ] ) / 1000000 )

    rewards_dict[ "total_last_month" ] = rewards_month

    return rewards_dict

def get_asset_details( valid_stake_address ):
    '''Get asset details and return list'''

    asset_list_output = []

    if valid_stake_address == "" :
        return asset_list_output

    asset_list = api.account_addresses_assets( valid_stake_address, return_type='json' )

    for asset in asset_list:
        asset_id = asset[ 'unit' ]
        asset_dict = {}

        asset_details = api.asset( asset_id, return_type='json' )
        asset_onchain_metadata = asset_details[ 'onchain_metadata' ]
        asset_metadata = asset_details[ 'metadata' ]
        asset_quantity = asset[ 'quantity' ]
        asset_img_link = ""
        asset_decimals = ""
        asset_ticker = ""
        asset_url = ""
        asset_logo = ""
        asset_name = ""

        try:
            asset_name = bytes.fromhex( asset_id[56:] ).decode( 'utf-8' )

        except UnicodeDecodeError:
            asset_name = bytes.fromhex( asset_id[56:] )
            print("UnicodeDecodeError")

        if asset_onchain_metadata :
            print("On Chain: ")
            print(asset_onchain_metadata)

            try:
                metadata_image = asset_onchain_metadata[ 'image' ]
                ipfs_id = metadata_image.partition( '//' )[-1]
                asset_img_link = f'{ IPFS_API_URL }{ ipfs_id }'

            except AttributeError:
                print("AttributeError " + asset_id )
            
            except KeyError:
                print("AttributeError " + asset_id )

            try:
                asset_name = asset_onchain_metadata[ 'name' ]
                
            except AttributeError:
                print("AttributeError " + asset_id )
            
            except KeyError:
                print("AttributeError " + asset_id )

        if asset_metadata :
            print("Metadata: ")
            print(asset_metadata)

            try:
                asset_name = asset_metadata[ 'name' ]

            except AttributeError:
                print("AttributeError " + asset_id )
            
            except KeyError:
                print("AttributeError " + asset_id )

            try:
                asset_decimals = asset_metadata[ 'decimals' ]
                asset_ticker = asset_metadata[ 'ticker' ]
                asset_url = asset_metadata[ 'url' ]
                #asset_logo = asset_metadata[ 'logo' ]
                asset_logo = ""

            except AttributeError:
                print("AttributeError " + asset_id )
            
            except KeyError:
                print("AttributeError " + asset_id )


        asset_dict["asset_id"] = asset_id
        asset_dict["asset_name"] = asset_name
        asset_dict["asset_img_link"] = asset_img_link
        asset_dict["asset_decimals"] = asset_decimals
        asset_dict["asset_ticker"] = asset_ticker
        asset_dict["asset_url"] = asset_url
        asset_dict["asset_logo"] = asset_logo
        asset_dict["asset_quantity"] = asset_quantity

        asset_list_output.append( asset_dict )

    return asset_list_output

def get_token_values( valid_asset_list ):
    '''Function for geting the Ada value of every token in the wallet of a given
    valid address. Price data provided by MinSwap'''

    token_list = []

    response = requests.get( MINSWAP_API_URL )

    if response.status_code != 200 :
        return token_list

    for asset in valid_asset_list:
        asset_id = asset[ "asset_id" ]
        token_dict = {}

        try:
            token_pair_info = response.json()[ asset_id + "_lovelace" ]
            token_price = float( token_pair_info[ "last_price" ] )
            token_quantity = asset[ "asset_quantity" ]

            token_dict[ "asset_name" ] = asset[ 'asset_name' ]
            token_dict[ "asset_img_link" ] = asset[ 'asset_img_link' ]
            token_dict[ "asset_decimals" ] = asset[ 'asset_decimals' ]
            token_dict[ "asset_ticker" ] = asset[ 'asset_ticker' ]
            token_dict[ "asset_url" ] = asset[ 'asset_url' ]
            token_dict[ "asset_logo" ] = asset[ 'asset_logo' ]
            token_dict[ "asset_price" ] = round( token_price, 2 )
            token_dict[ "asset_quantity" ] = token_quantity
            token_dict[ "asset_value" ] = round( token_price * float( token_quantity ) / 1000000, 2 )

            token_list.append( token_dict )

        except KeyError:
            print( "KeyError from " + asset_id )

    return token_list

def nft_request( url, asset ):
    '''Helper function to allow for easy implementation of
    multithreading of slow API getes for NFT data gathering'''

    asset_id = asset[ 'asset_id' ]

    nft_dict = {}
    policy_id = asset_id[ 0:56 ]

    asset_name = asset[ 'asset_name' ]

    nft_dict[ "asset_img_link" ] = asset[ 'asset_img_link' ]
    nft_dict[ "asset_decimals" ] = asset[ 'asset_decimals' ]
    nft_dict[ "asset_ticker" ] = asset[ 'asset_ticker' ]
    nft_dict[ "asset_url" ] = asset[ 'asset_url' ]
    nft_dict[ "asset_logo" ] = asset[ 'asset_logo' ]

    if policy_id == HANDLE_POLICY_ID :
        nft_dict[ "asset_name" ] = asset_name
        nft_dict[ "asset_value_floor" ] = 7.00
        nft_dict[ "collection_name" ] = "Ada Handle"
        nft_dict[ "best_trait" ] = "Error"
        nft_dict[ "asset_value" ] = -1

        if len( asset_name ) < 2 :
            nft_dict[ "best_trait" ] = "Legendary"
            nft_dict[ "asset_value" ] = -1

        elif len( asset_name ) < 3 :
            nft_dict[ "best_trait" ] = "Ultra Rare"
            nft_dict[ "asset_value" ] = 995.00

        elif len( asset_name ) < 4 :
            nft_dict[ "best_trait" ] = "Rare"
            nft_dict[ "asset_value" ] = 445.00

        elif len( asset_name ) < 8 :
            nft_dict[ "best_trait" ] = "Common"
            nft_dict[ "asset_value" ] = 80.00

        elif len( asset_name ) < 16 :
            nft_dict[ "best_trait" ] = "Basic"
            nft_dict[ "asset_value" ] = 15.00

        return nft_dict

    response = requests.get( url )

    if response.status_code != 200 :
        return {}

    collection_name = response.json()[ 'collection_name' ]
    trait_floors_dict = response.json()[ 'traitfloors' ]
    absolute_floor = response.json()[ 'floor' ]

    if absolute_floor is None:
        absolute_floor = 0

    trait_floors_dict_values = list(filter(None, (trait_floors_dict.values())))
    best_trait_floor = 0
    best_trait = "nothing"

    for trait in trait_floors_dict_values:
        trait_val = list(trait.values())[0]
        trait_key = list(trait.keys())[0]

        if trait_val > best_trait_floor :
            best_trait_floor = trait_val
            best_trait = trait_key

    nft_dict[ "asset_value" ] = float( best_trait_floor )
    nft_dict[ "asset_value_floor" ] = float( absolute_floor )
    nft_dict[ "best_trait" ] = best_trait
    nft_dict[ "collection_name" ] = collection_name

    nft_dict[ "asset_name" ] = asset_name
    nft_dict[ "asset_img_link" ] = asset[ 'asset_img_link' ]
    nft_dict[ "asset_decimals" ] = asset[ 'asset_decimals' ]
    nft_dict[ "asset_ticker" ] = asset[ 'asset_ticker' ]
    nft_dict[ "asset_url" ] = asset[ 'asset_url' ]
    nft_dict[ "asset_logo" ] = asset[ 'asset_logo' ]

    return nft_dict

def get_nft_values( valid_asset_list ):
    '''Function for geting the Ada value of every NFT in the
    wallet of a given valid address. Uses data from CNFTJungle'''

    nfts_list = []
    threads= []

    #Initializing the list of assets contained in the account, as well as the total controlled
    #amount of Ada which includes Ada in all addresses as well as rewards yet to be redeemed

    with ThreadPoolExecutor( max_workers=20 ) as executor:
        for asset in valid_asset_list:
            asset_id = asset[ "asset_id" ]
            url = CNFTJUNGLE_API_URL + asset_id

            threads.append( executor.submit( nft_request, url, asset ) )

        for task in as_completed( threads ):
            nft_dict = task.result()
            #does not show items worth zero, convenience right now, fix in future for wallet vs portfolio display
            if nft_dict and nft_dict[ 'asset_value' ] :
                nfts_list.append( nft_dict )

    return nfts_list

def sum_asset_values( assets_list ):
    '''Helper function that allows for easy summation of values
    of assets in lists, using the floor price of an NFTs rarest trait'''
    total_value = 0

    for asset in assets_list:
        total_value = total_value + asset[ "asset_value" ]

    return total_value

def sum_asset_values_floor( assets_list ):
    '''Helper function that allows for easy summation of values
    of assets in lists, using the floor price of an NFTs whole collection'''

    total_value = 0

    for asset in assets_list:
        total_value = total_value + asset[ "asset_value_floor" ]

    return total_value

def portfolio( request, addr = None ):
    '''Function to render the contents of the entered
    wallet address and the calculated values of the contained assets'''

    address = ""

    if request.method == 'GET' and not addr :
        return render( request, 'tools/portfolio_home.html' )

    if request.method == 'GET' and addr :
        address = addr

    if request.method == 'POST' :
        address = request.POST.get('addr', None)

    valid_address = validate_address( address )

    if not valid_address :
        return render( request, 'tools/portfolio_home_retry.html' )

    token_list = get_token_values( valid_address )
    nfts_list = get_nft_values( valid_address )
    ada_value = round( get_ada_value( valid_address ), 2)

    token_list_value = round( sum_asset_values( token_list ), 2 )
    nfts_list_value = round( sum_asset_values( nfts_list ), 2 )
    nfts_list_value_floor = round( sum_asset_values_floor( nfts_list ), 2 )

    total_value = round( ada_value + token_list_value + nfts_list_value, 2)
    total_value_using_floor = round( ada_value + token_list_value + nfts_list_value_floor, 2 )

    context = {
        'token_list' : token_list,
        'nfts_list' : nfts_list,
        'total_value' : total_value,
        'total_value_using_floor' : total_value_using_floor,
        'token_list_value' : token_list_value,
        'nfts_list_value_floor' : nfts_list_value_floor,
        'nfts_list_value' : nfts_list_value,
        'ada_value' : ada_value,
    }

    return render( request, 'tools/portfolio_results.html', context )

def summary( request, addr = None ):
    '''Function to render the contents of the entered
    wallet address and the calculated values of the contained assets'''

    address = ""

    if request.method == 'GET' and not addr :
        return render( request, 'tools/summary_home.html' )

    if request.method == 'GET' and addr :
        address = addr

    if request.method == 'POST' :
        address = request.POST.get('addr', None)

    valid_address = validate_address( address )

    if not valid_address :
        return render( request, 'tools/summary_home_retry.html' )

    token_list = get_token_values( valid_address )
    nfts_list = get_nft_values( valid_address )
    ada_value = round( get_ada_value( valid_address ), 2)

    token_list_value = round( sum_asset_values( token_list ), 2 )
    nfts_list_value = round( sum_asset_values( nfts_list ), 2 )
    nfts_list_value_floor = round( sum_asset_values_floor( nfts_list ), 2 )

    total_value = round( ada_value + token_list_value + nfts_list_value, 2)
    total_value_using_floor = round( ada_value + token_list_value + nfts_list_value_floor, 2 )

    rewards_dict = get_api_rewards_data( valid_address )

    total_rewards = round( rewards_dict[ "total_rewards" ], 2)
    total_withdrawals = round( rewards_dict[ "total_withdrawals" ], 2)
    total_withdrawable = round( rewards_dict[ "total_withdrawable" ], 2)
    pool_name = rewards_dict[ "pool_name" ]
    pool_ticker = rewards_dict[ "pool_ticker" ]
    total_last_month = round( rewards_dict[ "total_last_month" ], 2)

    context = {
        'token_list' : token_list,
        'nfts_list' : nfts_list,
        'total_value' : total_value,
        'total_value_using_floor' : total_value_using_floor,
        'token_list_value' : token_list_value,
        'nfts_list_value_floor' : nfts_list_value_floor,
        'nfts_list_value' : nfts_list_value,
        'ada_value' : ada_value,
        'total_rewards' : total_rewards,
        'total_withdrawals' : total_withdrawals,
        'total_withdrawable' : total_withdrawable,
        'pool_name' : pool_name,
        'pool_ticker' : pool_ticker,
        'total_last_month' : total_last_month,
    }

    return render( request, 'tools/summary_results.html', context )

def wallet( request, addr = None ):
    '''Function to render the contents of the entered
    wallet address and the calculated values of the contained assets'''

    address = ""

    if request.method == 'GET' and not addr :
        return render( request, 'tools/wallet_home.html' )

    if request.method == 'GET' and addr :
        address = addr

    if request.method == 'POST' :
        address = request.POST.get('addr', None)

    valid_address = validate_address( address )

    if not valid_address :
        return render( request, 'tools/wallet_home_retry.html' )

    asset_detail_list = get_asset_details( valid_address )

    token_list = get_token_values( asset_detail_list )

    nfts_list = get_nft_values( asset_detail_list )

    ada_value = round( get_ada_value( valid_address ), 2)

    context = {
        'token_list' : token_list,
        'nfts_list' : nfts_list,
        'ada_value' : ada_value,
    }

    return render( request, 'tools/wallet_results.html', context )

def staking( request, addr = None ):
    '''Function to render the staking details of the entered
    wallet address'''

    address = ""

    if request.method == 'GET' and not addr :
        return render( request, 'tools/staking_home.html' )

    if request.method == 'GET' and addr :
        address = addr

    if request.method == 'POST' :
        address = request.POST.get('addr', None)

    valid_address = validate_address( address )

    if not valid_address :
        return render( request, 'tools/staking_home_retry.html' )

    rewards_dict = get_api_rewards_data( valid_address )
    ada_value = round( get_ada_value( valid_address ), 2)

    total_rewards = round( rewards_dict[ "total_rewards" ], 2)
    total_withdrawals = round( rewards_dict[ "total_withdrawals" ], 2)
    total_withdrawable = round( rewards_dict[ "total_withdrawable" ], 2)
    pool_name = rewards_dict[ "pool_name" ]
    pool_ticker = rewards_dict[ "pool_ticker" ]
    total_last_month = round( rewards_dict[ "total_last_month" ], 2)

    context = {
        'total_rewards' : total_rewards,
        'total_withdrawals' : total_withdrawals,
        'total_withdrawable' : total_withdrawable,
        'pool_name' : pool_name,
        'pool_ticker' : pool_ticker,
        'total_last_month' : total_last_month,
        'ada_value' : ada_value,
    }

    return render( request, 'tools/staking_results.html', context )
    