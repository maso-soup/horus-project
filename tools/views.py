'''View File for Cardano Wallet Calculator functionality
of grander Cardano Apps Django Web application. '''

from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from blockfrost import ApiError, ApiUrls, BlockFrostApi
from django.shortcuts import render

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

def fetch_ada_value( valid_stake_address ):
    '''Function for fetching amount of Ada in the wallet of a given valid address'''
    ada_value = 0

    #If validStakeAddress is empty, it was invalidated by validateAddress function.
    if valid_stake_address == "" :
        return ada_value

    ada_value = float( api.accounts( valid_stake_address, return_type='json' )[ "controlled_amount" ] ) / 1000000
    return ada_value

def fetch_token_values( valid_stake_address ):
    '''Function for fetching the Ada value of every token in the wallet of a given
    valid address. Price data provided by MinSwap'''

    token_list = []

    #If validStakeAddress is empty, it was invalidated by validate_address function.
    if valid_stake_address == "" :
        return token_list

    asset_list = api.account_addresses_assets( valid_stake_address, return_type='json' )

    #Using minswap.org API for token prices
    response = requests.get( MINSWAP_API_URL )

    if response.status_code != 200 :
        return token_list

    for asset in asset_list:
        asset_id = asset["unit"]
        asset_name = bytes.fromhex( asset_id[56:] ).decode( 'utf-8' )

        try:
            token_dict = {}

            token_pair_info = response.json()[ asset_id + "_lovelace" ]
            token_price = float( token_pair_info[ "last_price" ] )
            token_quantity = asset[ "quantity" ]

            token_dict[ "asset_name" ] = asset_name
            token_dict[ "asset_price" ] = round( token_price, 2 )
            token_dict[ "asset_quantity" ] = token_quantity
            token_dict[ "asset_value" ] = round( token_price * float( token_quantity ) / 1000000, 2 )

            token_list.append( token_dict )

        except KeyError:
            print( "KeyError from " + asset_id )

    return token_list

def nft_request( url, asset_id ):
    '''Helper function to allow for easy implementation of
    multithreading of slow API fetches for NFT data gathering'''

    policy_id = asset_id[0:56]
    asset_name = bytes.fromhex( asset_id[56:] ).decode( 'utf-8' )
    nft_dict = {}

    if policy_id == HANDLE_POLICY_ID :
        nft_dict[ "asset_name" ] = asset_name
        nft_dict[ "asset_value_floor" ] = 7
        nft_dict[ "collection_name" ] = "Ada Handle"
        nft_dict[ "best_trait" ] = "Error"
        nft_dict[ "asset_value" ] = -1

        if len( asset_name ) < 2 :
            nft_dict[ "best_trait" ] = "Legendary"
            nft_dict[ "asset_value" ] = -1

        elif len( asset_name ) < 3 :
            nft_dict[ "best_trait" ] = "Ultra Rare"
            nft_dict[ "asset_value" ] = 995

        elif len( asset_name ) < 4 :
            nft_dict[ "best_trait" ] = "Rare"
            nft_dict[ "asset_value" ] = 445

        elif len( asset_name ) < 8 :
            nft_dict[ "best_trait" ] = "Common"
            nft_dict[ "asset_value" ] = 80

        elif len( asset_name ) < 16 :
            nft_dict[ "best_trait" ] = "Basic"
            nft_dict[ "asset_value" ] = 15

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
    best_trait = ""

    for trait in trait_floors_dict_values:
        trait_val = list(trait.values())[0]
        trait_key = list(trait.keys())[0]

        if trait_val > best_trait_floor :
            best_trait_floor = trait_val
            best_trait = trait_key

    nft_dict[ "asset_name" ] = asset_name
    nft_dict[ "asset_value" ] = float( best_trait_floor )
    nft_dict[ "asset_value_floor" ] = float( absolute_floor )
    nft_dict[ "best_trait" ] = best_trait
    nft_dict[ "collection_name" ] = collection_name

    return nft_dict

def fetch_nft_values( valid_stake_address ):
    '''Function for fetching the Ada value of every NFT in the
    wallet of a given valid address. Uses data from CNFTJungle'''

    nfts_list = []
    threads= []

    #If validStakeAddress is empty, it was invalidated by validateAddress function.
    if valid_stake_address == "" :
        return nfts_list

    #Initializing the list of assets contained in the account, as well as the total controlled
    #amount of Ada which includes Ada in all addresses as well as rewards yet to be redeemed
    asset_list = api.account_addresses_assets( valid_stake_address, return_type='json' )

    with ThreadPoolExecutor( max_workers=20 ) as executor:
        for asset in asset_list:
            asset_id = asset["unit"]
            url = CNFTJUNGLE_API_URL + asset_id

            threads.append( executor.submit( nft_request, url, asset_id ) )

        for task in as_completed( threads ):
            nft_dict = task.result()
            if nft_dict and nft_dict[ 'asset_value' ] :
                nfts_list.append( nft_dict )

    return nfts_list

def sum_asset_values( assets_list ):
    '''Helper function that allows for easy summation of values
    of assets in lists, using the floor price of an NFTs rarest trait'''
    total_value = 0

    for asset in assets_list:
        print(asset)
        print(asset["asset_value"])
        total_value = total_value + asset[ "asset_value" ]

    return total_value

def sum_asset_values_floor( assets_list ):
    '''Helper function that allows for easy summation of values
    of assets in lists, using the floor price of an NFTs whole collection'''

    total_value = 0

    for asset in assets_list:
        total_value = total_value + asset[ "asset_value_floor" ]

    return total_value

def prepare_context( valid_address ):
    '''Prepares the values to be rendedered in view functions'''

    token_list = fetch_token_values( valid_address )
    nfts_list = fetch_nft_values( valid_address )
    ada_value = round( fetch_ada_value( valid_address ), 2)

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

    return context

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

    context = prepare_context( valid_address )

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

    context = prepare_context( valid_address )

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

    context = prepare_context( valid_address )

    return render( request, 'tools/wallet_results.html', context )

def staking( request, addr = None ):
    '''Function to render the contents of the entered
    wallet address and the calculated values of the contained assets'''

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

    context = prepare_context( valid_address )

    return render( request, 'tools/staking_results.html', context )
    