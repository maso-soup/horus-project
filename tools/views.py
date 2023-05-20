'''View File for Cardano Wallet Calculator functionality
of grander Cardano Apps Django Web application. '''

from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from blockfrost import ApiError, ApiUrls, BlockFrostApi
from django.shortcuts import render

from time import perf_counter

#BlockFrost API which allows for querying the Cardano blockchain
api = BlockFrostApi(
    project_id='mainnetJZdBd2lCOXfHSI9ENhubJYAZ5ThYpXao',
    base_url=ApiUrls.mainnet.value,
)

#Official Ada Handle policy ID
HANDLE_POLICY_ID =  "f0ff48bbb7bbe9d59a40f1ce90e9e9d0ff5002ec48f232b49ca0fb9a"
#Rarities and prices of Ada Handles ( Legendary 1, Ultra Rare 2, Rare 3, Common 4-7, Basic 8-15 )
HANDLE_RARITIES = { "Legendary": -1, "Ultra Rare": 995, "Rare": 445, "Common": 80, "Basic": 15 }

CNFTJUNGLE_API_URL = "https://api.cnftjungle.app/assets/asset-info/"
MINSWAP_API_URL = "https://api-mainnet-prod.minswap.org/coinmarketcap/v2/pairs"
IPFS_API_URL = "https://ipfs.io/ipfs/"
LIQWID_API_URL = "https://api.liqwiddev.net/graphql"

LIQWID_FINANCE_ASSETS_POLICY_IDS_PLUS_ASSET_NAME = {"Ada":"lovelace", "DJED":"8db269c3ec630e06ae29f74bc39edd1f87c819f1056206e879a1cd61446a65644d6963726f555344", "SHEN":"8db269c3ec630e06ae29f74bc39edd1f87c819f1056206e879a1cd615368656e4d6963726f555344"}

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
            handle = input_address[1:].lower()

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

    account = api.accounts( valid_stake_address, return_type='json' )
    ada_value = float( account[ "controlled_amount" ] ) / 1000000

    return ada_value

def get_rewards_data( valid_stake_address ):
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

    pool_info = api.pool_metadata( pool_id, return_type='json' )
    print(pool_info)

    pool_ticker = pool_info[ "ticker" ]
    pool_name = pool_info[ "name" ]
    pool_homepage = pool_info[ "homepage" ]

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

def asset_request( asset ):
    '''Get asset details and return list'''

    t2_start = perf_counter()

    asset_id = asset[ 'unit' ]
    asset_dict = {}

    asset_details = api.asset( asset_id, return_type='json' )
    asset_onchain_metadata = asset_details[ 'onchain_metadata' ]
    asset_metadata = asset_details[ 'metadata' ]
    asset_quantity = float ( asset[ 'quantity' ] )
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

        try:
            metadata_image = asset_onchain_metadata[ 'image' ]
            ipfs_id = metadata_image.partition( '//' )[2]
            asset_img_link = f'{ IPFS_API_URL }{ ipfs_id }'
            if "ipfs/" in ipfs_id :
                ipfs_id = ipfs_id.partition( 'ipfs/' )[2]
                asset_img_link = f'{ IPFS_API_URL }{ ipfs_id }'

        except AttributeError:
            print("AttributeError Image Onchain " )
            if isinstance( metadata_image, list ) :
                ipfs_id_string = "".join( metadata_image )
                ipfs_id = ipfs_id_string.partition( '//' )[2]
                asset_img_link = f'{ IPFS_API_URL }{ ipfs_id }'

                if "ipfs/" in ipfs_id :
                    ipfs_id = ipfs_id.partition( 'ipfs/' )[2]
                    asset_img_link = f'{ IPFS_API_URL }{ ipfs_id }'

        except KeyError:
            print("KeyError Image Onchain " )

        try:
            asset_name = asset_onchain_metadata[ 'name' ]

        except AttributeError:
            print("AttributeError Onchain Name " + asset_id )

        except KeyError:
            print("KeyError Onchain Name " + asset_id )

    if asset_metadata :

        try:
            asset_name = asset_metadata[ 'name' ]

        except AttributeError:
            print("AttributeError Metadata Name " + asset_id )

        except KeyError:
            print("KeyError Metadata Name " + asset_id )

        try:
            asset_decimals = asset_metadata[ 'decimals' ]
            asset_ticker = asset_metadata[ 'ticker' ]
            asset_url = asset_metadata[ 'url' ]
            asset_logo = asset_metadata[ 'logo' ]
            if not asset_img_link :
                asset_img_link = "data:image/jpeg;base64," + asset_logo

        except AttributeError:
            print("AttributeError Metadata other" + asset_id )

        except KeyError:
            print("AttributeError Metadata other" + asset_id )


    asset_dict["asset_id"] = asset_id
    asset_dict["asset_name"] = asset_name
    asset_dict["asset_img_link"] = asset_img_link
    asset_dict["asset_ticker"] = asset_ticker
    asset_dict["asset_url"] = asset_url
    asset_dict["asset_quantity"] = asset_quantity

    if asset_decimals :
        asset_dict["asset_quantity"] = asset_quantity / pow(10, float( asset_decimals ) )

    if asset_dict["asset_quantity"] == 1 :
        asset_dict["asset_quantity"] = int (1)

    t2_stop = perf_counter()
    print(f'This asset {asset_name} took:  {t2_stop - t2_start}' )

    return asset_dict

def get_asset_details( valid_stake_address ):
    '''Function for geting the Ada value of every NFT in the
    wallet of a given valid address. Uses data from CNFTJungle'''
    t1_start = perf_counter()

    asset_list_output = []
    threads= []

    if valid_stake_address == "" :
        return asset_list_output

    valid_asset_list = api.account_addresses_assets( valid_stake_address, return_type='json' )

    with ThreadPoolExecutor() as executor:
        for asset in valid_asset_list:
            threads.append( executor.submit( asset_request, asset ) )

        for task in as_completed( threads ):
            asset_dict = task.result()
            asset_list_output.append( asset_dict )

    t1_stop = perf_counter()
    print("All Detail Assets took: ", t1_stop - t1_start )

    return asset_list_output

def get_token_values( valid_asset_list ):
    '''Function for geting the Ada value of every token in the wallet of a given
    valid address. Price data provided by MinSwap'''
    t1_start = perf_counter()

    token_list = []

    response = requests.get( MINSWAP_API_URL )

    if response.status_code != 200 :
        return token_list

    response_JSON = response.json()

    for asset in valid_asset_list:
        asset_id = asset[ "asset_id" ]
        token_dict = asset

        asset_pair = asset_id + "_lovelace"

        if asset_pair in response_JSON :
            token_pair_info = response_JSON[ asset_id + "_lovelace" ]
            token_price = float( token_pair_info[ "last_price" ] )
            token_quantity = asset[ "asset_quantity" ]

            token_dict[ "asset_price" ] = round( token_price, 2 )
            token_dict[ "asset_value" ] = round( token_price * token_quantity, 2 )

            token_list.append( token_dict )

    t1_stop = perf_counter()
    print("Token Values took: ", t1_stop - t1_start )

    return token_list

def nft_request( url, asset ):
    '''Helper function to allow for easy implementation of
    multithreading of slow API gets for NFT data gathering'''
    t1_start = perf_counter()

    asset_id = asset[ 'asset_id' ]

    nft_dict = asset
    policy_id = asset_id[ 0:56 ]

    asset_name = asset[ 'asset_name' ]

    if policy_id == HANDLE_POLICY_ID :
        nft_dict[ "asset_value_floor" ] = 7.00
        nft_dict[ "collection_name" ] = "Ada Handle"

        if len( asset_name ) - 1  < 2 :
            nft_dict[ "best_trait" ] = "Legendary"
            nft_dict[ "asset_value" ] = -1

        elif len( asset_name ) - 1 < 3 :
            nft_dict[ "best_trait" ] = "Ultra Rare"
            nft_dict[ "asset_value" ] = 995.00

        elif len( asset_name ) - 1 < 4 :
            nft_dict[ "best_trait" ] = "Rare"
            nft_dict[ "asset_value" ] = 445.00

        elif len( asset_name ) - 1 < 8 :
            nft_dict[ "best_trait" ] = "Common"
            nft_dict[ "asset_value" ] = 80.00

        elif len( asset_name ) - 1 < 16 :
            nft_dict[ "best_trait" ] = "Basic"
            nft_dict[ "asset_value" ] = 15.00

        else :
            nft_dict[ "best_trait" ] = "Error"
            nft_dict[ "asset_value" ] = -1

        return nft_dict

    response = requests.get( url )

    if response.status_code != 200 :
        return {}

    nft_data = response.json()

    collection_name = nft_data[ 'collection_name' ]
    trait_floors_dict = nft_data[ 'traitfloors' ]
    absolute_floor = nft_data[ 'floor' ]

    if absolute_floor is None:
        absolute_floor = 0

    trait_floors_dict_values = list( filter( None, ( trait_floors_dict.values() ) ) )
    best_trait_floor = 0
    best_trait = "nothing"

    for trait in trait_floors_dict_values:
        trait_val = list(trait.values())[0]
        trait_key = list(trait.keys())[0]

        if trait_val > best_trait_floor :
            best_trait_floor = trait_val
            best_trait = trait_key

    nft_dict[ "asset_value" ] = float( best_trait_floor ) if best_trait_floor else absolute_floor
    nft_dict[ "asset_value_floor" ] = float( absolute_floor )
    nft_dict[ "best_trait" ] = best_trait
    nft_dict[ "collection_name" ] = collection_name

    t1_stop = perf_counter()
    print("This single NFT took: ", t1_stop - t1_start )

    return nft_dict

def get_nft_values( valid_asset_list ):
    '''Function for geting the Ada value of every NFT in the
    wallet of a given valid address. Uses data from CNFTJungle'''
    t1_start = perf_counter()

    nfts_list = []
    threads= []

    #Initializing the list of assets contained in the account, as well as the total controlled
    #amount of Ada which includes Ada in all addresses as well as rewards yet to be redeemed

    with ThreadPoolExecutor() as executor:
        for asset in valid_asset_list:
            asset_id = asset[ "asset_id" ]
            url = CNFTJUNGLE_API_URL + asset_id

            threads.append( executor.submit( nft_request, url, asset ) )

        for task in as_completed( threads ):
            nft_dict = task.result()
            #does not show items worth zero, convenience right now, fix in future for wallet vs portfolio display
            if nft_dict and nft_dict[ 'asset_value' ] :
                nfts_list.append( nft_dict )

    t1_stop = perf_counter()
    print("All NFTs took: ", t1_stop - t1_start )

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

    asset_detail_list = get_asset_details( valid_address )

    token_list = get_token_values( asset_detail_list )
    nfts_list = get_nft_values( asset_detail_list )
    sorted_token_list = sorted( token_list, key = lambda item: item[ 'asset_value' ], reverse=True )
    sorted_nfts_list = sorted( nfts_list, key = lambda item: item[ 'asset_value' ], reverse=True )

    ada_value = round( get_ada_value( valid_address ), 2)

    token_list_value = round( sum_asset_values( token_list ), 2 )
    nfts_list_value = round( sum_asset_values( nfts_list ), 2 )
    nfts_list_value_floor = round( sum_asset_values_floor( nfts_list ), 2 )

    total_value = round( ada_value + token_list_value + nfts_list_value, 2 )
    total_value_using_floor = round( ada_value + token_list_value + nfts_list_value_floor, 2 )

    rewards_dict = get_rewards_data( valid_address )

    total_rewards = round( rewards_dict[ "total_rewards" ], 2 )
    total_withdrawals = round( rewards_dict[ "total_withdrawals" ], 2 )
    total_withdrawable = round( rewards_dict[ "total_withdrawable" ], 2 )
    pool_name = rewards_dict[ "pool_name" ]
    pool_ticker = rewards_dict[ "pool_ticker" ]
    pool_homepage = rewards_dict[ "pool_homepage" ]
    total_last_month = round( rewards_dict[ "total_last_month" ], 2 )

    context = {
        'token_list' : sorted_token_list,
        'nfts_list' : sorted_nfts_list,
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
        'pool_homepage' : pool_homepage,
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
    sorted_asset_detailed_list = sorted( asset_detail_list, key = lambda item: item[ 'asset_name' ] )

    ada_value = round( get_ada_value( valid_address ), 2 )

    context = {
        'asset_detail_list' : sorted_asset_detailed_list,
        'ada_value' : ada_value,
    }

    return render( request, 'tools/wallet_results.html', context )

def faq( request ):
    return render( request, 'tools/faq.html' )

def get_token_price( policyassetID ):
    response = requests.get( MINSWAP_API_URL, timeout=5 )

    if policyassetID == "lovelace":
        return 1

    if response.status_code != 200 :
        return "Minswap API Error"

    response_json = response.json()

    token_pair_info = response_json[ policyassetID + "_lovelace" ]
    return float( token_pair_info[ "last_price" ] )

def calculate_lq_current_rewards( markets_list, user_staked_lq_proprotion, lq_price ):

    lq_reward_dist_supply_ratio = 1
    min_lq_rewards_per_market = 500 / 30
    num_markets = 3
    num_stable_markets = 1
    min_lq_rewards = 50000 / 30
    max_lq_rewards = 100000 / 30
    adjusted_min_lq_rewards = min_lq_rewards - ( min_lq_rewards_per_market * num_markets )
    adjusted_max_lq_rewards = max_lq_rewards - ( min_lq_rewards_per_market * num_markets )
    target_stablecoin_apr = 0.5

    combined_total_market_borrow_interest_ada_value_daily = 0
    stable_total_market_supply_interest_ada_value_daily = 0
    shen_total_market_supply_interest_ada_value_daily = 0
    ada_total_market_supply_interest_ada_value_daily = 0
    stable_user_ada_value_supplied_int_gen = 0
    stable_user_ada_value_borrowed_int_gen = 0
    shen_user_ada_value_supplied_int_gen = 0
    shen_user_ada_value_borrowed_int_gen = 0
    ada_user_ada_value_supplied_int_gen = 0
    ada_user_ada_value_borrowed_int_gen = 0
    combined_user_ada_value_supply = 0

    combined_stablecoin_supply_ada_value = 0
    combined_stablecoin_borrow_interest_ada_value = 0

    for market in markets_list:
        combined_total_market_borrow_interest_ada_value_daily += market[ "total_market_borrow_interest_ada_value_daily" ]
        if ( market[ "market_id" ] == "DJED" or market[ "market_id" ] == "iUSD" ):
            stable_user_ada_value_borrowed_int_gen += market[ "user_ada_value_borrowed_int_gen" ]
            stable_user_ada_value_supplied_int_gen += market[ "user_ada_value_supplied_int_gen" ]
            stable_total_market_supply_interest_ada_value_daily += market[ "total_market_supply_interest_ada_value_daily" ]
            combined_user_ada_value_supply += market[ "user_ada_value_supplied" ]

            combined_stablecoin_supply_ada_value += market[ "total_ada_value_supplied" ]
            combined_stablecoin_borrow_interest_ada_value += market[ "total_market_borrow_interest_ada_value_daily" ]

        elif market[ "market_id" ] == "SHEN" :
            shen_user_ada_value_borrowed_int_gen += market[ "user_ada_value_borrowed_int_gen" ]
            shen_user_ada_value_supplied_int_gen += market[ "user_ada_value_supplied_int_gen" ]
            shen_total_market_supply_interest_ada_value_daily += market[ "total_market_supply_interest_ada_value_daily" ]
            combined_user_ada_value_supply += market[ "user_ada_value_supplied" ]

            shen_borrow_interest_ada_value = market[ "total_market_borrow_interest_ada_value_daily" ]

        elif market[ "market_id" ] == "Ada" :
            ada_user_ada_value_borrowed_int_gen += market[ "user_ada_value_borrowed_int_gen" ]
            ada_user_ada_value_supplied_int_gen += market[ "user_ada_value_supplied_int_gen" ]
            ada_total_market_supply_interest_ada_value_daily += market[ "total_market_supply_interest_ada_value_daily" ]
            combined_user_ada_value_supply += market[ "user_ada_value_supplied" ]

            ada_borrow_interest_ada_value = market[ "total_market_borrow_interest_ada_value_daily" ]


    stable_rewards_stable_value_daily = combined_stablecoin_supply_ada_value * ( target_stablecoin_apr / 365 )
    stable_rewards_lq_value_daily = stable_rewards_stable_value_daily / lq_price
    print(f"Total stable LQ rewards daily: {stable_rewards_lq_value_daily}" )
    total_rewards_lq_value_daily = stable_rewards_lq_value_daily / ( combined_stablecoin_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily )
    
    variable_total_rewards_lq_value_daily = total_rewards_lq_value_daily - ( min_lq_rewards_per_market * num_markets )

    print(f"Total LQ rewards daily: {total_rewards_lq_value_daily} minimum is {min_lq_rewards}" )

    #####Delete between, this is testing no scaling factor

    lq_reward_dist_stable_supply_daily = ( ( variable_total_rewards_lq_value_daily * ( combined_stablecoin_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) ) + ( min_lq_rewards_per_market * num_stable_markets ) ) * lq_reward_dist_supply_ratio
    lq_reward_dist_stable_borrow_daily = ( ( variable_total_rewards_lq_value_daily * ( combined_stablecoin_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) ) + ( min_lq_rewards_per_market * num_stable_markets ) ) * ( 1 - lq_reward_dist_supply_ratio )

    lq_reward_dist_shen_supply_daily = ( ( variable_total_rewards_lq_value_daily * ( shen_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) ) +  min_lq_rewards_per_market ) * lq_reward_dist_supply_ratio
    lq_reward_dist_shen_borrow_daily = ( ( variable_total_rewards_lq_value_daily * ( shen_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) ) + min_lq_rewards_per_market ) * ( 1 - lq_reward_dist_supply_ratio )

    lq_reward_dist_ada_supply_daily = ( ( variable_total_rewards_lq_value_daily * ( ada_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) ) + min_lq_rewards_per_market ) * lq_reward_dist_supply_ratio
    lq_reward_dist_ada_borrow_daily = ( ( variable_total_rewards_lq_value_daily * ( ada_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) ) + min_lq_rewards_per_market ) * ( 1 - lq_reward_dist_supply_ratio )

    print(f"Non-Adjusted Stable LQ rewards daily: {lq_reward_dist_stable_supply_daily}" )
    print(f"Non-Adjusted Shen LQ rewards daily: {lq_reward_dist_shen_supply_daily}" )
    print(f"Non-Adjusted Ada LQ rewards daily: {lq_reward_dist_ada_supply_daily}" )

    ####

    scaling_factor = 1

    if variable_total_rewards_lq_value_daily > adjusted_max_lq_rewards :
        scaling_factor = adjusted_max_lq_rewards / variable_total_rewards_lq_value_daily
    
    elif variable_total_rewards_lq_value_daily < adjusted_min_lq_rewards:
        scaling_factor = adjusted_min_lq_rewards / variable_total_rewards_lq_value_daily

    lq_reward_dist_stable_supply_daily = ( ( variable_total_rewards_lq_value_daily * ( combined_stablecoin_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) * scaling_factor ) + ( min_lq_rewards_per_market * num_stable_markets ) ) * lq_reward_dist_supply_ratio
    lq_reward_dist_stable_borrow_daily = ( ( variable_total_rewards_lq_value_daily * ( combined_stablecoin_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) * scaling_factor ) + ( min_lq_rewards_per_market * num_stable_markets ) ) * ( 1 - lq_reward_dist_supply_ratio )

    lq_reward_dist_shen_supply_daily = ( ( variable_total_rewards_lq_value_daily * ( shen_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) * scaling_factor ) +  min_lq_rewards_per_market ) * lq_reward_dist_supply_ratio
    lq_reward_dist_shen_borrow_daily = ( ( variable_total_rewards_lq_value_daily * ( shen_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily )  * scaling_factor ) + min_lq_rewards_per_market ) * ( 1 - lq_reward_dist_supply_ratio )

    lq_reward_dist_ada_supply_daily = ( ( variable_total_rewards_lq_value_daily * ( ada_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) * scaling_factor ) + min_lq_rewards_per_market ) * lq_reward_dist_supply_ratio
    lq_reward_dist_ada_borrow_daily = ( ( variable_total_rewards_lq_value_daily * ( ada_borrow_interest_ada_value / combined_total_market_borrow_interest_ada_value_daily ) * scaling_factor ) + min_lq_rewards_per_market ) * ( 1 - lq_reward_dist_supply_ratio )

    print(f"Adjusted Stable LQ rewards daily: {lq_reward_dist_stable_supply_daily}" )
    print(f"Adjusted Shen LQ rewards daily: {lq_reward_dist_shen_supply_daily}" )
    print(f"Adjusted Ada LQ rewards daily: {lq_reward_dist_ada_supply_daily}" )
        
    stable_supply_proportion = stable_user_ada_value_supplied_int_gen / stable_total_market_supply_interest_ada_value_daily
    stable_borrow_proportion = stable_user_ada_value_borrowed_int_gen / combined_total_market_borrow_interest_ada_value_daily

    shen_supply_proportion = shen_user_ada_value_supplied_int_gen / shen_total_market_supply_interest_ada_value_daily
    shen_borrow_proportion = shen_user_ada_value_borrowed_int_gen / combined_total_market_borrow_interest_ada_value_daily

    ada_supply_proportion = ada_user_ada_value_supplied_int_gen / ada_total_market_supply_interest_ada_value_daily
    ada_borrow_proportion = ada_user_ada_value_borrowed_int_gen / combined_total_market_borrow_interest_ada_value_daily

    lq_reward_supply_stable_daily = lq_reward_dist_stable_supply_daily * stable_supply_proportion
    lq_reward_borrow_stable_daily = lq_reward_dist_stable_borrow_daily * stable_borrow_proportion

    lq_reward_supply_shen_daily = lq_reward_dist_shen_supply_daily * shen_supply_proportion
    lq_reward_borrow_shen_daily = lq_reward_dist_shen_borrow_daily * shen_borrow_proportion

    lq_reward_supply_ada_daily = lq_reward_dist_ada_supply_daily * ada_supply_proportion
    lq_reward_borrow_ada_daily = lq_reward_dist_ada_borrow_daily * ada_borrow_proportion

    total_protocol_revenue_ada_value = combined_total_market_borrow_interest_ada_value_daily * 0.1
    user_protocol_revenue_ada_value = combined_total_market_borrow_interest_ada_value_daily * 0.1 * user_staked_lq_proprotion

    lq_reward_supply_stable_daily_ada_value = ( lq_reward_dist_stable_supply_daily * lq_price ) * stable_supply_proportion
    lq_reward_borrow_stable_daily_ada_value = ( lq_reward_dist_stable_borrow_daily * lq_price ) * stable_borrow_proportion

    lq_reward_supply_shen_daily_ada_value = ( lq_reward_dist_shen_supply_daily * lq_price ) * shen_supply_proportion
    lq_reward_borrow_shen_daily_ada_value = ( lq_reward_dist_shen_borrow_daily * lq_price ) * shen_borrow_proportion

    lq_reward_supply_ada_daily_ada_value = ( lq_reward_dist_ada_supply_daily * lq_price ) * ada_supply_proportion
    lq_reward_borrow_ada_daily_ada_value = ( lq_reward_dist_ada_borrow_daily * lq_price ) * ada_borrow_proportion

    print(f"Original Total LQ Rewards {total_rewards_lq_value_daily} vs Adjusted Total LQ Rewards {lq_reward_dist_stable_supply_daily + lq_reward_dist_shen_supply_daily + lq_reward_dist_ada_supply_daily}")

    lq_rewards_total_apr = 0

    if combined_user_ada_value_supply > 0:
        lq_rewards_total_apr =  ( lq_reward_supply_stable_daily_ada_value + lq_reward_supply_shen_daily_ada_value + lq_reward_supply_ada_daily_ada_value ) / combined_user_ada_value_supply * 100 * 365

    lq_rewards_dict = {
        "lq_reward_supply_stable_daily" : lq_reward_supply_stable_daily,
        "lq_reward_borrow_stable_daily" : lq_reward_borrow_stable_daily,
        "lq_reward_supply_stable_daily_ada_value" : lq_reward_supply_stable_daily_ada_value,
        "lq_reward_borrow_stable_daily_ada_value" : lq_reward_borrow_stable_daily_ada_value,
        "lq_reward_supply_shen_daily" : lq_reward_supply_shen_daily,
        "lq_reward_borrow_shen_daily" : lq_reward_borrow_shen_daily,
        "lq_reward_supply_shen_daily_ada_value" : lq_reward_supply_shen_daily_ada_value,
        "lq_reward_borrow_shen_daily_ada_value" : lq_reward_borrow_shen_daily_ada_value,
        "lq_reward_supply_ada_daily" : lq_reward_supply_ada_daily,
        "lq_reward_borrow_ada_daily" : lq_reward_borrow_ada_daily,
        "lq_reward_supply_ada_daily_ada_value" : lq_reward_supply_ada_daily_ada_value,
        "lq_reward_borrow_ada_daily_ada_value" : lq_reward_borrow_ada_daily_ada_value,
        "total_protocol_revenue_ada_value" : total_protocol_revenue_ada_value,
        "user_protocol_revenue_ada_value" : user_protocol_revenue_ada_value,
        "lq_rewards_total_apr" : lq_rewards_total_apr,
    }
    
    return lq_rewards_dict

def get_lq_staking_details( params_total_ada_value, staking_address, lq_price ):
    
    user_staked_lq = params_total_ada_value / lq_price
    staked_lq_address = api.address( staking_address, return_type='json' )
    total_staked_lq = 0
    
    for a in staked_lq_address[ "amount" ]:
        if a[ "unit" ] == "da8c30857834c6ae7203935b89278c532b3995245295456f993e1d244c51" :
            total_staked_lq += float( a[ "quantity" ] ) / 1000000

    user_staked_lq_proportion = user_staked_lq / total_staked_lq

    lq_staking_dict = {
        "user_staked_lq_proportion" : user_staked_lq_proportion,
        "total_staked_lq" : total_staked_lq,
        "lq_price" : lq_price
    }

    return lq_staking_dict

def get_market_current_data( user_token_supply, user_token_borrow, market, stake_apy, user_staked_lq_proportion ):

    revenue_share_percentage = 0.1
    market_dict = {}

    market_id = market[ "marketId" ]
    market_dict[ "market_id" ] = market_id
    
    if market_id == "Ada" :
        token_price = 1
        stake_daily_apr = ( ( 1 + stake_apy ) ** ( 1/365 ) ) - 1

    else:
        token_price = get_token_price( LIQWID_FINANCE_ASSETS_POLICY_IDS_PLUS_ASSET_NAME[ market_id ] )
        stake_daily_apr = 0

    utilization = float( market[ "utilization" ] )
    token_liquidity = float ( market [ "totalSupply" ] ) / 1000000
    total_token_supplied = token_liquidity / ( 1 - utilization )
    print("Total token supplied: ", total_token_supplied)
    total_token_borrowed = total_token_supplied * utilization

    borrow_daily_apr = ( ( 1 + float( market[ "borrowApy" ] ) ) ** ( 1/365 ) ) - 1
    supply_daily_apr = ( ( 1 + float( market[ "supplyApy" ] ) ) ** ( 1/365 ) ) - 1

    supply_revenue_daily = supply_daily_apr * user_token_supply
    borrow_interest_daily = borrow_daily_apr * user_token_borrow

    market_dict[ "supply_revenue_daily" ] = supply_revenue_daily
    market_dict[ "borrow_interest_daily" ] = -borrow_interest_daily

    total_ada_value_supplied = total_token_supplied * token_price
    total_ada_value_borrowed = total_token_borrowed * token_price

    market_dict[ "total_ada_value_supplied" ] = total_ada_value_supplied
    market_dict[ "total_ada_value_borrowed" ] = total_ada_value_borrowed

    total_market_supply_interest_daily = total_token_supplied * supply_daily_apr
    total_market_borrow_interest_daily = total_token_borrowed * borrow_daily_apr
    total_market_supply_interest_ada_value_daily = total_ada_value_supplied * supply_daily_apr
    total_market_borrow_interest_ada_value_daily = total_ada_value_borrowed * borrow_daily_apr

    market_dict[ "total_market_revenue_daily" ] = total_market_borrow_interest_daily * revenue_share_percentage
    market_dict[ "user_market_revenue_daily" ] = total_market_borrow_interest_daily * 0.1 * user_staked_lq_proportion

    user_ada_value_supplied = user_token_supply * token_price
    user_ada_value_borrowed = user_token_borrow * token_price

    market_dict[ "user_ada_value_supplied" ] = user_ada_value_supplied
    market_dict[ "user_ada_value_borrowed" ] = user_ada_value_borrowed

    stake_revenue_daily = stake_daily_apr * user_token_supply * ( 1 - utilization )
    
    market_dict[ "stake_revenue_daily" ] = stake_revenue_daily

    #market_dict[ "user_ada_value_supplied" ] = user_ada_value_supplied
    market_dict[ "user_ada_value_supplied_int_gen" ] = user_ada_value_supplied * supply_daily_apr
    market_dict[ "user_ada_value_borrowed_int_gen" ] = user_ada_value_borrowed * borrow_daily_apr
    market_dict[ "total_market_supply_interest_ada_value_daily" ] = total_market_supply_interest_ada_value_daily
    market_dict[ "total_market_borrow_interest_ada_value_daily" ] = total_market_borrow_interest_ada_value_daily

    return market_dict

def get_liqwid_current_data( params_list ):

    post_payload = {
        "operationName": "GetMarkets",
        "variables": {},
        "query": "query GetMarkets {\n  markets {\n    ...MarketFragment\n    __typename\n  }\n}\n\nfragment MarketFragment on Market {\n  asset {\n    symbol\n    icon\n    marketId\n    name\n    __typename\n  }\n  decimals\n  market {\n    ...MarketInfoFragment\n    __typename\n  }\n  marketParams {\n    ...MarketParamsDatumFragment\n    __typename\n  }\n  marketId\n  maxLoanToValue\n  borrowApy\n  supplyApy\n  totalSupply\n  supplyLqDistributionApy\n  borrowLqDistributionApy\n  exchangeRate\n  qTokenId\n  qTokenPolicyId\n  minValue\n  compoundsInAYear\n  utilization\n  __typename\n}\n\nfragment MarketInfoFragment on MarketInfo {\n  params {\n    multiSigStSymbol\n    marketId\n    oracleTokenClass {\n      ...AssetClassFragment\n      __typename\n    }\n    underlyingClass {\n      ...FixedTokenFragment\n      __typename\n    }\n    uniqRef {\n      ...UniqueRefFragment\n      __typename\n    }\n    __typename\n  }\n  scripts {\n    action {\n      ...ScriptPlutusV2Fragment\n      __typename\n    }\n    actionToken {\n      ...ScriptMintingPolicyFragment\n      __typename\n    }\n    batch {\n      ...ScriptPlutusV2Fragment\n      __typename\n    }\n    batchFinal {\n      ...ScriptPlutusV2Fragment\n      __typename\n    }\n    batchToken {\n      ...ScriptMintingPolicyFragment\n      __typename\n    }\n    borrowToken {\n      ...ScriptMintingPolicyFragment\n      __typename\n    }\n    collateralParamsToken {\n      ...ScriptMintingPolicyFragment\n      __typename\n    }\n    liquidation {\n      ...ScriptMintingPolicyFragment\n      __typename\n    }\n    loan {\n      ...ScriptPlutusV2Fragment\n      __typename\n    }\n    marketParamsToken {\n      ...ScriptMintingPolicyFragment\n      __typename\n    }\n    marketState {\n      ...ScriptPlutusV2Fragment\n      __typename\n    }\n    marketStateToken {\n      ...ScriptMintingPolicyFragment\n      __typename\n    }\n    qToken {\n      ...ScriptMintingPolicyFragment\n      __typename\n    }\n    __typename\n  }\n  __typename\n}\n\nfragment AssetClassFragment on AssetClass {\n  name\n  symbol\n  __typename\n}\n\nfragment FixedTokenFragment on FixedToken {\n  value0 {\n    ...AssetClassFragment\n    __typename\n  }\n  __typename\n}\n\nfragment UniqueRefFragment on UniqueRef {\n  index\n  transactionId\n  __typename\n}\n\nfragment ScriptPlutusV2Fragment on ScriptPlutusV2 {\n  script {\n    value0\n    value1 {\n      _empty\n      __typename\n    }\n    __typename\n  }\n  hash\n  __typename\n}\n\nfragment ScriptMintingPolicyFragment on ScriptMintingPolicy {\n  script {\n    value0 {\n      value0\n      value1 {\n        _empty\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n  assetClass {\n    ...AssetClassFragment\n    __typename\n  }\n  __typename\n}\n\nfragment MarketParamsDatumFragment on MarketParamsDatum {\n  actionDistribution\n  actionHash\n  actionStakeCredentials\n  batchHash\n  closeFactor0\n  closeFactor1\n  compoundRate\n  dividendsDatum {\n    value0 {\n      value0\n      __typename\n    }\n    __typename\n  }\n  dividendsValidatorHash\n  incomeRatio {\n    treasury\n    suppliers\n    reserve\n    dividends\n    __typename\n  }\n  initialQTokenRate\n  interestModel {\n    baseRate\n    utilMultiplier\n    utilMultiplierJump\n    kink\n    __typename\n  }\n  liquidationThreshold0\n  liquidationThreshold1\n  loanValidatorHash\n  maxBatchTime\n  maxCollateralAssets\n  maxLTV\n  maxLoan\n  maxTimeWidth\n  minBatchSize\n  minBatchTime\n  minValue\n  numActions\n  treasuryDatum {\n    value0 {\n      value0\n      __typename\n    }\n    __typename\n  }\n  treasuryValidatorHash\n  __typename\n}"
    }
    response = requests.post( LIQWID_API_URL, json=post_payload, timeout=5 )

    if response.status_code != 200 :
        return "Liqwid API error"

    liqwid_api_data = response.json()
    liqwid_markets_data = liqwid_api_data[ "data" ][ "markets" ]

    print("Params list ", params_list[0])

    lq_price = get_token_price( "da8c30857834c6ae7203935b89278c532b3995245295456f993e1d244c51" )

    params_total_ada_value = params_list[0] * lq_price
    params_list.pop(0)

    lq_staking_details = get_lq_staking_details( params_total_ada_value, "addr1w8arvq7j9qlrmt0wpdvpp7h4jr4fmfk8l653p9t907v2nsss7w7r4", lq_price )

    markets_list = []
    param_counter = 0
    user_token_supply = 0
    user_token_borrow = 0

    for market in liqwid_markets_data:
        
        user_token_supply = params_list[ param_counter ]
        user_token_borrow = params_list[ param_counter + 1]
        market_data_dict = get_market_current_data( user_token_supply, user_token_borrow, market, 0.0305, lq_staking_details[ "user_staked_lq_proportion" ] )
        param_counter += 2

        markets_list.append( market_data_dict )

    lq_rewards = calculate_lq_current_rewards( markets_list, lq_staking_details[ "user_staked_lq_proportion" ], lq_price )

    output_data = {
        "markets_list" : markets_list,
        "lq_rewards" : lq_rewards,
        "lq_price" : lq_price,
        "total_staked_lq" : lq_staking_details[ "total_staked_lq" ],
    }

    return output_data

def liqwid_current( request ):

    if request.method == 'GET' :
        return render( request, 'tools/liqwid_current.html' )

    if request.method == 'POST' :
        try:
            user_data = request.POST.getlist('data', None)
            data_list = [ float( d ) if d != "" else 0.0 for d in user_data ]

        except ValueError :
            return render( request, 'tools/liqwid_current.html' )

        try:
            liqwid_data = get_liqwid_current_data( data_list )
        
        except requests.exceptions.ReadTimeout:
            return render( request, 'tools/liqwid_current.html' )

        return render( request, 'tools/liqwid_current_results.html', context=liqwid_data )

    return render( request, 'tools/liqwid_current.html' )